-- =============================================================================
-- PostgreSQL — inicialização dos bancos de dados
-- Executado UMA ÚNICA VEZ quando o volume do Postgres é criado.
-- =============================================================================

-- Banco de metadados da aplicação (catálogo, logs de ingestão, users)
-- O banco principal já é criado pela env var POSTGRES_DB no container.

-- Banco dedicado para o Prefect
CREATE DATABASE prefect;

-- Conceder privilégios ao usuário padrão
GRANT ALL PRIVILEGES ON DATABASE prefect TO educacao;
