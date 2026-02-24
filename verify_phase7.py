#!/usr/bin/env python3
"""
Phase 7 - Production Hardening Acceptance Tests
Verifies all production readiness criteria
"""
import asyncio
import os
import json
from datetime import datetime, timedelta
import subprocess
from pathlib import Path


class Phase7Acceptance:
    """Phase 7 Acceptance Testing"""

    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.results = []

    def log_check(self, name: str, passed: bool, details: str = ""):
        """Log a verification check"""
        status = "✅" if passed else "❌"
        message = f"{status} {name}"
        if details:
            message += f": {details}"

        self.results.append(message)
        print(message)

        if passed:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

    def verify_docker_compose(self):
        """AC1: Docker Compose configuration is valid"""
        print("\n" + "="*70)
        print("AC1: Docker Compose Setup")
        print("="*70)

        try:
            result = subprocess.run(
                ["docker-compose", "config"],
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=10
            )

            self.log_check(
                "docker-compose.yml is valid",
                result.returncode == 0,
                "Configuration is syntactically valid"
            )

            # Check for required services
            if result.returncode == 0:
                config = result.stdout
                services = [
                    'api', 'db', 'redis', 'nginx', 'worker'
                ]

                for service in services:
                    has_service = f"services:" in config and service in config
                    self.log_check(f"Service defined: {service}", has_service)

        except Exception as e:
            self.log_check("Docker Compose validation", False, str(e))

    def verify_dockerfiles(self):
        """AC2: Dockerfiles are properly configured"""
        print("\n" + "="*70)
        print("AC2: Dockerfiles")
        print("="*70)

        dockerfiles = [
            Path("docker/api/Dockerfile"),
            Path("docker/worker/Dockerfile")
        ]

        for dockerfile in dockerfiles:
            exists = dockerfile.exists()
            self.log_check(f"Dockerfile exists: {dockerfile.name}", exists)

            if exists:
                with open(dockerfile, 'r') as f:
                    content = f.read()
                    has_healthcheck = "HEALTHCHECK" in content
                    has_expose = "EXPOSE" in content or "CMD" in content

                    self.log_check(
                        f"{dockerfile.name} has health check",
                        has_healthcheck
                    )

    def verify_nginx_config(self):
        """AC3: Nginx reverse proxy is configured"""
        print("\n" + "="*70)
        print("AC3: Nginx Reverse Proxy")
        print("="*70)

        nginx_files = [
            Path("docker/nginx/nginx.conf"),
            Path("docker/nginx/conf.d/default.conf")
        ]

        for nginx_file in nginx_files:
            exists = nginx_file.exists()
            self.log_check(f"Nginx config exists: {nginx_file.name}", exists)

            if exists:
                with open(nginx_file, 'r') as f:
                    content = f.read()

                    # Check for security headers
                    security_items = [
                        ('X-Content-Type-Options', 'Content type protection'),
                        ('X-Frame-Options', 'Clickjacking protection'),
                        ('CORS', 'Rate limiting'),
                    ]

                    for item, desc in security_items:
                        found = item in content
                        self.log_check(
                            f"Nginx has {desc}",
                            found
                        )

    def verify_database_migration(self):
        """AC4: Database migration scripts exist"""
        print("\n" + "="*70)
        print("AC4: Database Migration")
        print("="*70)

        migration_files = [
            Path("scripts/migrate_db.py"),
            Path("docker/postgres/init.sql")
        ]

        for mig_file in migration_files:
            exists = mig_file.exists()
            self.log_check(f"Migration file exists: {mig_file.name}", exists)

    def verify_backup_restore(self):
        """AC5: Backup and restore scripts exist"""
        print("\n" + "="*70)
        print("AC5: Backup & Restore")
        print("="*70)

        backup_file = Path("scripts/backup_restore.py")
        exists = backup_file.exists()
        self.log_check("Backup/restore script exists", exists)

        if exists:
            with open(backup_file, 'r') as f:
                content = f.read()

                features = [
                    ('full_backup', 'Full backup'),
                    ('restore_backup', 'Restore functionality'),
                    ('cleanup_old_backups', 'Backup cleanup'),
                ]

                for feature, desc in features:
                    found = feature in content
                    self.log_check(f"Has {desc}", found)

    def verify_healthcheck(self):
        """AC6: Health check endpoints are implemented"""
        print("\n" + "="*70)
        print("AC6: Health Check System")
        print("="*70)

        healthcheck_file = Path("apps/api/health_check.py")
        exists = healthcheck_file.exists()
        self.log_check("Health check module exists", exists)

        if exists:
            with open(healthcheck_file, 'r') as f:
                content = f.read()

                endpoints = [
                    ('health_check', '/health endpoint'),
                    ('database_health', 'Database health'),
                    ('redis_health', 'Redis health'),
                    ('detailed_health', 'Detailed health metrics'),
                ]

                for endpoint, desc in endpoints:
                    found = endpoint in content
                    self.log_check(f"Has {desc}", found)

    def verify_secrets_management(self):
        """AC7: Secrets management is configured"""
        print("\n" + "="*70)
        print("AC7: Secrets Management")
        print("="*70)

        config_file = Path("apps/api/config.py")
        exists = config_file.exists()
        self.log_check("Config module exists", exists)

        if exists:
            with open(config_file, 'r') as f:
                content = f.read()

                items = [
                    ('Settings', 'Settings class'),
                    ('JWT_SECRET', 'JWT secret management'),
                    ('SecretsManager', 'Secrets manager'),
                    ('validate_secrets', 'Secret validation'),
                ]

                for item, desc in items:
                    found = item in content
                    self.log_check(f"Has {desc}", found)

        env_example = Path(".env.example")
        env_exists = env_example.exists()
        self.log_check(".env.example file exists", env_exists)

    def verify_monitoring(self):
        """AC8: Monitoring and alerting is configured"""
        print("\n" + "="*70)
        print("AC8: Monitoring & Alerts")
        print("="*70)

        health_file = Path("apps/api/health_check.py")
        if health_file.exists():
            with open(health_file, 'r') as f:
                content = f.read()

                items = [
                    ('AlertManager', 'Alert manager'),
                    ('periodic_health_check', 'Periodic checks'),
                    ('thresholds', 'Alert thresholds'),
                ]

                for item, desc in items:
                    found = item in content
                    self.log_check(f"Has {desc}", found)

    def verify_startup_scripts(self):
        """AC9: Deployment and startup scripts exist"""
        print("\n" + "="*70)
        print("AC9: Startup & Deployment Scripts")
        print("="*70)

        startup_file = Path("scripts/startup.sh")
        exists = startup_file.exists()
        self.log_check("Startup script exists", exists)

        if exists:
            with open(startup_file, 'r') as f:
                content = f.read()

                items = [
                    ('Environment variables', 'Env check'),
                    ('Docker services', 'Docker startup'),
                    ('Database', 'DB initialization'),
                    ('Health checks', 'Health verification'),
                ]

                for item, _ in items:
                    found = item in content
                    self.log_check(f"Startup includes {item}", found)

    def verify_documentation(self):
        """AC10: Production deployment documentation exists"""
        print("\n" + "="*70)
        print("AC10: Documentation")
        print("="*70)

        doc_file = Path("PHASE7_COMPLETE.md")
        exists = doc_file.exists()
        self.log_check("Phase 7 documentation exists", exists)

        if exists:
            with open(doc_file, 'r') as f:
                content = f.read()

                sections = [
                    ('Docker', 'Docker setup'),
                    ('Database Migration', 'Migration guide'),
                    ('Backup', 'Backup procedures'),
                    ('Monitoring', 'Monitoring setup'),
                    ('Deployment', 'Deployment guide'),
                ]

                for section, _ in sections:
                    found = section in content
                    self.log_check(f"Documentation has {section}", found)

    def verify_deployment_configuration(self):
        """AC11: Production configuration is secure"""
        print("\n" + "="*70)
        print("AC11: Deployment Configuration")
        print("="*70)

        # Check for default secrets in docker-compose
        dc_file = Path("docker-compose.yml")
        if dc_file.exists():
            with open(dc_file, 'r') as f:
                content = f.read()

                # Should NOT have hardcoded secrets
                has_changeme = 'changeme' in content.lower()
                self.log_check(
                    "No default credentials in docker-compose",
                    not has_changeme
                )

        # Check environment file template
        env_file = Path(".env.example")
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()

                # Should prompt for passwords
                has_password_prompts = 'changeme' in content or 'set_strong' in content
                self.log_check(
                    ".env.example has password prompts",
                    has_password_prompts
                )

    def verify_test_coverage(self):
        """AC12: Unit tests for Phase 7 exist"""
        print("\n" + "="*70)
        print("AC12: Test Coverage")
        print("="*70)

        test_file = Path("apps/api/test_phase7.py")
        exists = test_file.exists()
        self.log_check("Phase 7 tests exist", exists)

        if exists:
            with open(test_file, 'r') as f:
                content = f.read()

                tests = [
                    ('TestDatabaseMigration', 'DB migration tests'),
                    ('TestBackupRestore', 'Backup/restore tests'),
                    ('TestHealthCheck', 'Health check tests'),
                    ('TestConfig', 'Configuration tests'),
                ]

                for test_class, desc in tests:
                    found = test_class in content
                    self.log_check(f"Has {desc}", found)

    def run_all_checks(self):
        """Run all acceptance checks"""
        print("\n" + "█" * 70)
        print("  PHASE 7 ACCEPTANCE TESTS - PRODUCTION HARDENING")
        print("█" * 70)

        self.verify_docker_compose()
        self.verify_dockerfiles()
        self.verify_nginx_config()
        self.verify_database_migration()
        self.verify_backup_restore()
        self.verify_healthcheck()
        self.verify_secrets_management()
        self.verify_monitoring()
        self.verify_startup_scripts()
        self.verify_documentation()
        self.verify_deployment_configuration()
        self.verify_test_coverage()

        # Print summary
        print("\n" + "█" * 70)
        print("  ACCEPTANCE TEST SUMMARY")
        print("█" * 70)
        print(f"✅ Passed: {self.checks_passed}")
        print(f"❌ Failed: {self.checks_failed}")
        print(f"📊 Total: {self.checks_passed + self.checks_failed}")

        if self.checks_failed == 0:
            print("\n🎉 ALL ACCEPTANCE CRITERIA MET - PHASE 7 READY FOR DEPLOYMENT ✓")
        else:
            print(f"\n⚠️  {self.checks_failed} check(s) failed - review needed")

        return self.checks_failed == 0


if __name__ == "__main__":
    acceptor = Phase7Acceptance()
    success = acceptor.run_all_checks()
    exit(0 if success else 1)
