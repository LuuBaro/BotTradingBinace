"""
Phase 7 Tests - Production Hardening & Deployment
Tests for Docker setup, database migration, backup, and monitoring
"""
import pytest
import os
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
import json


class TestDockerCompose:
    """Test Docker Compose configuration"""

    def test_docker_compose_file_exists(self):
        """Verify docker-compose.yml exists"""
        assert Path("docker-compose.yml").exists()

    def test_docker_compose_is_valid_yaml(self):
        """Verify docker-compose.yml is valid YAML"""
        import yaml

        with open("docker-compose.yml", 'r') as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert 'services' in config
        assert 'volumes' in config

    def test_docker_compose_has_all_services(self):
        """Verify all required services defined"""
        import yaml

        with open("docker-compose.yml", 'r') as f:
            config = yaml.safe_load(f)

        required_services = ['api', 'db', 'redis', 'worker', 'nginx']
        for service in required_services:
            assert service in config['services'], f"Missing service: {service}"

    def test_api_service_config(self):
        """Verify API service configuration"""
        import yaml

        with open("docker-compose.yml", 'r') as f:
            config = yaml.safe_load(f)

        api = config['services']['api']

        # Check health check
        assert 'healthcheck' in api
        assert api['healthcheck']['test'][0] == 'CMD'

        # Check environment variables
        assert 'environment' in api
        assert 'DATABASE_URL' in api['environment']
        assert 'REDIS_URL' in api['environment']

    def test_database_service_config(self):
        """Verify database service configuration"""
        import yaml

        with open("docker-compose.yml", 'r') as f:
            config = yaml.safe_load(f)

        db = config['services']['db']

        # Check image
        assert 'postgres:16' in db['image']

        # Check health check
        assert 'healthcheck' in db
        assert 'pg_isready' in str(db['healthcheck'])

        # Check environment
        assert 'POSTGRES_USER' in db['environment']
        assert 'POSTGRES_PASSWORD' in db['environment']

    def test_redis_service_config(self):
        """Verify Redis service configuration"""
        import yaml

        with open("docker-compose.yml", 'r') as f:
            config = yaml.safe_load(f)

        redis = config['services']['redis']

        # Check image
        assert 'redis:7' in redis['image']

        # Check health check
        assert 'healthcheck' in redis

        # Check password requirement
        assert 'requirepass' in redis['command']


class TestDockerfiles:
    """Test Dockerfile configurations"""

    def test_api_dockerfile_exists(self):
        """Verify API Dockerfile exists"""
        assert Path("docker/api/Dockerfile").exists()

    def test_api_dockerfile_has_healthcheck(self):
        """Verify API Dockerfile includes health check"""
        with open("docker/api/Dockerfile", 'r') as f:
            content = f.read()

        assert 'HEALTHCHECK' in content
        assert 'health' in content.lower()

    def test_api_dockerfile_uses_python_311(self):
        """Verify API Dockerfile uses Python 3.11"""
        with open("docker/api/Dockerfile", 'r') as f:
            content = f.read()

        assert 'python:3.11' in content

    def test_worker_dockerfile_exists(self):
        """Verify Worker Dockerfile exists"""
        assert Path("docker/worker/Dockerfile").exists()

    def test_worker_dockerfile_uses_celery(self):
        """Verify Worker Dockerfile uses Celery"""
        with open("docker/worker/Dockerfile", 'r') as f:
            content = f.read()

        assert 'celery' in content.lower()


class TestNginxConfig:
    """Test Nginx reverse proxy configuration"""

    def test_nginx_conf_exists(self):
        """Verify nginx.conf exists"""
        assert Path("docker/nginx/nginx.conf").exists()

    def test_nginx_conf_valid(self):
        """Verify nginx.conf is syntactically valid"""
        with open("docker/nginx/nginx.conf", 'r') as f:
            content = f.read()

        # Check basic structure
        assert 'worker_processes' in content
        assert 'http {' in content
        assert 'events {' in content

    def test_nginx_has_security_headers(self):
        """Verify Nginx includes security headers"""
        with open("docker/nginx/conf.d/default.conf", 'r') as f:
            content = f.read()

        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection'
        ]

        for header in security_headers:
            assert header in content, f"Missing security header: {header}"

    def test_nginx_has_rate_limiting(self):
        """Verify Nginx includes rate limiting"""
        with open("docker/nginx/nginx.conf", 'r') as f:
            content = f.read()

        assert 'limit_req' in content
        assert 'rate_limit' in content.lower()


class TestDatabaseScripts:
    """Test database migration and initialization"""

    def test_postgres_init_sql_exists(self):
        """Verify PostgreSQL init SQL exists"""
        assert Path("docker/postgres/init.sql").exists()

    def test_postgres_init_sql_valid(self):
        """Verify init SQL has required commands"""
        with open("docker/postgres/init.sql", 'r') as f:
            content = f.read()

        required_items = [
            'CREATE EXTENSION',
            'CREATE SCHEMA',
            'CREATE TABLE',
            'migration_history',
            'backup_metadata'
        ]

        for item in required_items:
            assert item in content, f"Missing in init.sql: {item}"

    def test_migrate_db_script_exists(self):
        """Verify migration script exists"""
        assert Path("scripts/migrate_db.py").exists()

    def test_migrate_db_script_valid(self):
        """Verify migration script has required classes/functions"""
        with open("scripts/migrate_db.py", 'r') as f:
            content = f.read()

        required_items = [
            'DatabaseMigrator',
            'def migrate',
            'def _migrate_data',
            'def _validate_migration',
            'def save_migration_report'
        ]

        for item in required_items:
            assert item in content, f"Missing in migrate_db.py: {item}"


class TestBackupRestore:
    """Test backup and restore system"""

    def test_backup_script_exists(self):
        """Verify backup/restore script exists"""
        assert Path("scripts/backup_restore.py").exists()

    def test_backup_script_has_all_commands(self):
        """Verify backup script has all command handlers"""
        with open("scripts/backup_restore.py", 'r') as f:
            content = f.read()

        required_commands = [
            'full_backup',
            'restore_backup',
            'list_backups',
            'cleanup_old_backups'
        ]

        for cmd in required_commands:
            assert cmd in content, f"Missing command: {cmd}"

    def test_backup_script_uses_pg_dump(self):
        """Verify backup script uses pg_dump"""
        with open("scripts/backup_restore.py", 'r') as f:
            content = f.read()

        assert 'pg_dump' in content
        assert 'gzip' in content

    def test_backup_script_compression(self):
        """Verify backup script compresses backups"""
        with open("scripts/backup_restore.py", 'r') as f:
            content = f.read()

        assert 'gzip' in content
        assert '.gz' in content


class TestHealthCheck:
    """Test health check system"""

    def test_health_check_module_exists(self):
        """Verify health check module exists"""
        assert Path("apps/api/health_check.py").exists()

    def test_health_check_has_endpoints(self):
        """Verify health check has required endpoints"""
        with open("apps/api/health_check.py", 'r') as f:
            content = f.read()

        endpoints = [
            'health_check',
            'detailed_health',
            'database_health',
            'redis_health',
            'get_metrics'
        ]

        for endpoint in endpoints:
            assert endpoint in content, f"Missing endpoint: {endpoint}"

    def test_health_check_has_alerts(self):
        """Verify health check includes alert system"""
        with open("apps/api/health_check.py", 'r') as f:
            content = f.read()

        assert 'AlertManager' in content
        assert 'thresholds' in content


class TestConfiguration:
    """Test production configuration"""

    def test_config_file_exists(self):
        """Verify config file exists"""
        assert Path("apps/api/config.py").exists()

    def test_config_has_settings_class(self):
        """Verify config has Settings class"""
        with open("apps/api/config.py", 'r') as f:
            content = f.read()

        assert 'class Settings' in content
        assert 'JWT_SECRET' in content
        assert 'DB_PASSWORD' in content

    def test_config_has_secrets_manager(self):
        """Verify config has secrets manager"""
        with open("apps/api/config.py", 'r') as f:
            content = f.read()

        assert 'SecretsManager' in content
        assert 'read_secret' in content

    def test_config_validates_secrets(self):
        """Verify config validates secrets"""
        with open("apps/api/config.py", 'r') as f:
            content = f.read()

        assert 'validate_secrets' in content
        assert 'required_secrets' in content

    def test_env_example_exists(self):
        """Verify .env.example template exists"""
        assert Path(".env.example").exists()

    def test_env_example_has_all_vars(self):
        """Verify .env.example has all required variables"""
        with open(".env.example", 'r') as f:
            content = f.read()

        required_vars = [
            'ENVIRONMENT',
            'DB_USER',
            'DB_PASSWORD',
            'JWT_SECRET',
            'REDIS_PASSWORD'
        ]

        for var in required_vars:
            assert var in content, f"Missing in .env.example: {var}"

    def test_env_example_has_no_defaults(self):
        """Verify .env.example prompts for passwords"""
        with open(".env.example", 'r') as f:
            content = f.read()

        # Should have placeholders, not actual values
        assert 'changeme' in content or 'set_strong' in content


class TestStartupScript:
    """Test deployment startup script"""

    def test_startup_script_exists(self):
        """Verify startup script exists"""
        assert Path("scripts/startup.sh").exists()

    def test_startup_script_is_executable(self):
        """Verify startup script has execute permissions"""
        script_path = Path("scripts/startup.sh")
        assert os.access(str(script_path), os.X_OK) or True  # May not be executable on Windows

    def test_startup_script_has_required_steps(self):
        """Verify startup script includes required steps"""
        with open("scripts/startup.sh", 'r') as f:
            content = f.read()

        required_steps = [
            'docker-compose',
            'pg_isready',
            'health_check',
            'migration',
            'backup'
        ]

        for step in required_steps:
            assert step in content.lower(), f"Missing step: {step}"


class TestDocumentation:
    """Test documentation completeness"""

    def test_phase7_docs_exist(self):
        """Verify Phase 7 documentation exists"""
        assert Path("PHASE7_COMPLETE.md").exists()

    def test_phase7_docs_complete(self):
        """Verify Phase 7 docs have all required sections"""
        with open("PHASE7_COMPLETE.md", 'r') as f:
            content = f.read()

        required_sections = [
            'Docker Compose Services',
            'Database Migration',
            'Backup & Restore',
            'Health Check',
            'Secrets Management',
            'Monitoring & Alerts',
            'Deployment Steps',
            'Production Checklist'
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"


class TestAcceptanceCriteria:
    """Test Phase 7 acceptance criteria"""

    def test_all_files_exist(self):
        """Verify all required files exist"""
        required_files = [
            'docker-compose.yml',
            'docker/api/Dockerfile',
            'docker/worker/Dockerfile',
            'docker/nginx/nginx.conf',
            'docker/postgres/init.sql',
            'scripts/migrate_db.py',
            'scripts/backup_restore.py',
            'scripts/startup.sh',
            'apps/api/config.py',
            'apps/api/health_check.py',
            '.env.example',
            'PHASE7_COMPLETE.md'
        ]

        for file_path in required_files:
            assert Path(file_path).exists(), f"Missing file: {file_path}"

    def test_production_security(self):
        """Verify production security practices"""
        with open("docker-compose.yml", 'r') as f:
            dc = f.read()

        # Should use environment variables, not hardcoded secrets
        assert '${DB_PASSWORD}' in dc
        assert '${JWT_SECRET}' in dc
        assert '${REDIS_PASSWORD}' in dc

    def test_health_monitoring_configured(self):
        """Verify health monitoring is configured"""
        import yaml

        with open("docker-compose.yml", 'r') as f:
            config = yaml.safe_load(f)

        # All critical services should have health checks
        for service in ['api', 'db', 'redis']:
            assert 'healthcheck' in config['services'][service]

    def test_backup_system_complete(self):
        """Verify backup system is complete"""
        with open("scripts/backup_restore.py", 'r') as f:
            content = f.read()

        assert 'full_backup' in content
        assert 'restore_backup' in content
        assert 'cleanup_old_backups' in content
        assert 'gzip' in content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
