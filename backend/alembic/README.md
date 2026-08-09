# Alembic

O modelo SQLAlchemy pode ser comparado com o banco usando Alembic. A fonte canônica
das migrações aplicadas ao Supabase é `supabase/migrations`, porque ela também contém
RLS, grants, policies de Storage, funções e triggers que não são representados pelo
metadata do SQLAlchemy.

Não aplique uma revisão Alembic e uma migração Supabase com a mesma alteração.
