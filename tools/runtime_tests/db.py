# -*- coding: utf-8 -*-
"""Postgres side of scenario A (hops.yaml H3, design.md 2.): schema, roles, and the checks of the DB tests.

Roles (design.md 2.「RLS をすり抜ける主体を作らない」):
  owner     bootstrap superuser of the container; used only to create the roles below
  migrator  NOSUPERUSER, owns the tables (the migration role); the application never connects as it
  app_rls   NOSUPERUSER NOBYPASSRLS LOGIN; the application role; not a member of migrator
The tables have ENABLE and FORCE ROW LEVEL SECURITY, the policy tenant_id = current_setting('app.tenant', true),
tenant_id NOT NULL and CHECK (tenant_id <> '').

For the detector to be shown working, a second schema `broken` repeats the casestudy's weaker set-up (an app role with
BYPASSRLS, a table without FORCE owned by the app role, a SECURITY DEFINER function and a view without security_invoker):
the bypass-actor check must report each of them.
"""
import secrets

import psycopg

SCHEMA_SQL = """
DROP SCHEMA IF EXISTS app CASCADE; DROP SCHEMA IF EXISTS broken CASCADE;
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='migrator') THEN CREATE ROLE migrator NOLOGIN NOSUPERUSER NOBYPASSRLS; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='app_rls') THEN CREATE ROLE app_rls LOGIN NOSUPERUSER NOBYPASSRLS; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='app_bypass') THEN CREATE ROLE app_bypass LOGIN NOSUPERUSER BYPASSRLS; END IF;
END $$;
CREATE SCHEMA app AUTHORIZATION migrator;
SET ROLE migrator;
CREATE TABLE app.tenants (id text PRIMARY KEY CHECK (id <> ''), status text NOT NULL);
CREATE TABLE app.invoices (id int PRIMARY KEY, tenant_id text NOT NULL CHECK (tenant_id <> ''), owner_sub text NOT NULL, amount int NOT NULL);
ALTER TABLE app.invoices ENABLE ROW LEVEL SECURITY; ALTER TABLE app.invoices FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON app.invoices USING (tenant_id = current_setting('app.tenant', true));
ALTER TABLE app.tenants ENABLE ROW LEVEL SECURITY; ALTER TABLE app.tenants FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_self ON app.tenants USING (id = current_setting('app.tenant', true));
GRANT USAGE ON SCHEMA app TO app_rls; GRANT SELECT ON app.tenants, app.invoices TO app_rls;
RESET ROLE;
ALTER ROLE app_rls SET search_path = app;
CREATE SCHEMA broken;
CREATE TABLE broken.invoices (id int PRIMARY KEY, tenant_id text NOT NULL, owner_sub text NOT NULL, amount int NOT NULL);
ALTER TABLE broken.invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON broken.invoices USING (tenant_id = current_setting('app.tenant', true));
ALTER TABLE broken.invoices OWNER TO app_bypass;
CREATE VIEW broken.all_invoices AS SELECT * FROM broken.invoices;
ALTER VIEW broken.all_invoices OWNER TO app_bypass;
CREATE MATERIALIZED VIEW broken.invoice_totals AS SELECT tenant_id, sum(amount) AS total FROM broken.invoices GROUP BY tenant_id;
ALTER MATERIALIZED VIEW broken.invoice_totals OWNER TO app_bypass;
CREATE FUNCTION broken.count_all() RETURNS bigint LANGUAGE sql SECURITY DEFINER AS 'SELECT count(*) FROM broken.invoices';
ALTER FUNCTION broken.count_all() OWNER TO app_bypass;
GRANT USAGE ON SCHEMA broken TO app_rls, app_bypass; GRANT SELECT ON broken.invoices, broken.all_invoices TO app_rls;
GRANT EXECUTE ON FUNCTION broken.count_all() TO app_rls;
"""


def connect(env, user, password, **kw):
    return psycopg.connect(host='localhost', port=35432, dbname='saas', user=user, password=password, **kw)


def setup(env, alice_sub, carol_sub, bob_sub):
    """Create schema and roles; return passwords of the login roles (random per run)."""
    pw = {'app_rls': secrets.token_urlsafe(16), 'app_bypass': secrets.token_urlsafe(16)}
    with connect(env, 'owner', env.pg_password, autocommit=True) as c:
        c.execute(SCHEMA_SQL)
        for role, p in pw.items():
            c.execute(psycopg.sql.SQL('ALTER ROLE {} PASSWORD {}').format(psycopg.sql.Identifier(role), psycopg.sql.Literal(p)))
        # the superuser inserts the fixtures (FORCE makes the policy apply to migrator too, and no tenant is set here)
        c.execute("INSERT INTO app.tenants VALUES ('t1','active'),('t2','active')")
        c.execute('INSERT INTO app.invoices VALUES (1,%s,%s,1000),(2,%s,%s,2000),(3,%s,%s,3000)',
                  ('t2', bob_sub, 't1', alice_sub, 't1', carol_sub))
        c.execute("INSERT INTO broken.invoices VALUES (1,'t2','b',1000),(2,'t1','a',2000)")
    return pw


def set_tenant_status(env, tenant, status):
    with connect(env, 'owner', env.pg_password, autocommit=True) as c:
        c.execute('UPDATE app.tenants SET status = %s WHERE id = %s', (status, tenant))


BYPASS_QUERIES = {
    # current_user and every role it can SET ROLE to (membership): a member of a BYPASSRLS or superuser role can switch to it
    'app role is superuser or BYPASSRLS': "SELECT r.rolname FROM pg_roles r WHERE pg_has_role(current_user, r.oid, 'MEMBER') AND (r.rolsuper OR r.rolbypassrls)",
    'app role owns a table of the schema': "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                                          "WHERE n.nspname = %(s)s AND c.relkind IN ('r','p') AND pg_has_role(current_user, c.relowner, 'MEMBER')",
    'table without RLS or without FORCE': "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                                         "WHERE n.nspname = %(s)s AND c.relkind IN ('r','p') AND NOT (c.relrowsecurity AND c.relforcerowsecurity)",
    'SECURITY DEFINER function': "SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = %(s)s AND p.prosecdef",
    'view without security_invoker': "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %(s)s "
                                    "AND c.relkind = 'v' AND NOT coalesce('security_invoker=true' = ANY (c.reloptions) OR 'security_invoker=on' = ANY (c.reloptions), false)",
    'materialized view (RLS does not apply)': "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %(s)s AND c.relkind = 'm'",
}


def bypass_actors(conn, schema):
    """A04: run as the application's role; return {check: [hits]} (empty lists = no actor can bypass RLS)."""
    out = {}
    for name, q in BYPASS_QUERIES.items():
        rows = conn.execute(q, {'s': schema}).fetchall() if '%(s)s' in q else conn.execute(q).fetchall()
        out[name] = [r[0] for r in rows]
    return out
