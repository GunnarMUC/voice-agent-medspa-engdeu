#!/usr/bin/env python3
"""
Mac Security Audit Script
Automatically inventories software, checks for security issues, and applies updates.
Created by Claude - Anthropic AI Assistant
"""

import os
import sys
import json
import subprocess
import datetime
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

class MacSecurityAuditor:
    def __init__(self, output_dir: str = ".", dry_run: bool = False, auto_update: bool = False):
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run
        self.auto_update = auto_update
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        self.setup_logging()
        
        # Results storage
        self.inventory = {}
        self.security_issues = []
        self.updates_applied = []
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.output_dir / f"security_audit_{self.timestamp}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def run_command(self, command: str, shell: bool = True) -> Tuple[str, int]:
        """Run shell command and return output and return code"""
        try:
            if isinstance(command, str) and shell:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
            else:
                result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            return result.stdout.strip(), result.returncode
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {command}")
            return "", 1
        except Exception as e:
            self.logger.error(f"Error running command '{command}': {e}")
            return "", 1

    def inventory_applications(self) -> Dict[str, List[str]]:
        """Inventory all installed applications"""
        self.logger.info("🔍 Starting application inventory...")
        
        apps = {
            "user_applications": [],
            "system_applications": [],
            "system_utilities": [],
            "homebrew_packages": [],
            "ai_models": [],
            "python_packages": [],
            "node_packages": []
        }
        
        # User Applications
        output, _ = self.run_command("ls -1 /Applications | grep -E '\\.app$' | sed 's/\\.app$//'")
        if output:
            apps["user_applications"] = [app.strip() for app in output.split('\n') if app.strip()]
            
        # System Applications
        output, _ = self.run_command("ls -1 /System/Applications | grep -E '\\.app$' | sed 's/\\.app$//'")
        if output:
            apps["system_applications"] = [app.strip() for app in output.split('\n') if app.strip()]
            
        # System Utilities
        output, _ = self.run_command("ls -1 /System/Applications/Utilities | grep -E '\\.app$' | sed 's/\\.app$//'")
        if output:
            apps["system_utilities"] = [app.strip() for app in output.split('\n') if app.strip()]
            
        # Homebrew packages
        output, _ = self.run_command("which brew && brew list --formula 2>/dev/null")
        if output and "brew list" not in output:
            apps["homebrew_packages"] = [pkg.strip() for pkg in output.split('\n') if pkg.strip()]
            
        # Ollama AI models
        output, _ = self.run_command("which ollama && ollama list 2>/dev/null | tail -n +2")
        if output and "ollama list" not in output:
            models = []
            for line in output.split('\n'):
                if line.strip() and not line.startswith('NAME'):
                    parts = line.split()
                    if len(parts) >= 3:
                        models.append(f"{parts[0]} ({parts[2]})")
            apps["ai_models"] = models
            
        # Python packages
        output, _ = self.run_command("python3 -m pip list --format=freeze 2>/dev/null")
        if output:
            packages = []
            for line in output.split('\n'):
                if line.strip() and '==' in line:
                    packages.append(line.strip())
            apps["python_packages"] = packages[:50]  # Limit for readability
            
        # Node.js global packages
        output, _ = self.run_command("which npm && npm list -g --depth=0 --json 2>/dev/null")
        if output and output.startswith('{'):
            try:
                npm_data = json.loads(output)
                if 'dependencies' in npm_data:
                    apps["node_packages"] = list(npm_data['dependencies'].keys())
            except json.JSONDecodeError:
                pass
                
        self.inventory = apps
        self.logger.info(f"✅ Inventory complete: {sum(len(v) for v in apps.values())} items found")
        return apps

    def check_security_issues(self) -> List[Dict]:
        """Check for security vulnerabilities and outdated software"""
        self.logger.info("🔒 Checking for security issues...")
        
        issues = []
        
        # Check macOS updates
        output, _ = self.run_command("softwareupdate -l 2>/dev/null")
        if "Software Update found the following" in output:
            for line in output.split('\n'):
                if "* Label:" in line or "Title:" in line:
                    issues.append({
                        "type": "macos_update",
                        "severity": "high",
                        "description": f"macOS system update available: {line.strip()}",
                        "fix_command": "sudo softwareupdate -i -a"
                    })
        
        # Check pip version
        output, _ = self.run_command("python3 -m pip --version")
        if output:
            pip_version = output.split()[1] if len(output.split()) > 1 else "unknown"
            # Simple version check - if less than 24.0, it's likely outdated
            try:
                major_version = int(pip_version.split('.')[0])
                if major_version < 24:
                    issues.append({
                        "type": "python_pip",
                        "severity": "critical",
                        "description": f"pip version {pip_version} is outdated (security risk)",
                        "fix_command": "python3 -m pip install --upgrade pip"
                    })
            except (ValueError, IndexError):
                pass
        
        # Check outdated Python packages
        output, _ = self.run_command("python3 -m pip list --outdated --format=json 2>/dev/null")
        if output and output.startswith('['):
            try:
                outdated = json.loads(output)
                security_packages = ['lxml', 'anthropic', 'openai', 'httpx-sse', 'requests', 'urllib3', 'cryptography']
                for pkg in outdated:
                    if pkg['name'].lower() in security_packages:
                        issues.append({
                            "type": "python_package",
                            "severity": "high" if pkg['name'].lower() in ['lxml', 'requests', 'urllib3'] else "medium",
                            "description": f"Security-relevant package {pkg['name']} outdated: {pkg['version']} → {pkg['latest_version']}",
                            "fix_command": f"python3 -m pip install --upgrade {pkg['name']}"
                        })
            except json.JSONDecodeError:
                pass
        
        # Check Homebrew outdated packages
        output, _ = self.run_command("which brew && brew outdated 2>/dev/null")
        if output:
            security_brews = ['curl', 'openssl', 'git', 'node', 'python']
            for line in output.split('\n'):
                pkg_name = line.split()[0] if line.strip() else ""
                if any(sec_pkg in pkg_name.lower() for sec_pkg in security_brews):
                    issues.append({
                        "type": "homebrew_package",
                        "severity": "medium",
                        "description": f"Security-relevant Homebrew package outdated: {line.strip()}",
                        "fix_command": f"brew upgrade {pkg_name}"
                    })
        
        # Check Node.js version
        output, _ = self.run_command("node --version 2>/dev/null")
        if output:
            node_version = output.replace('v', '')
            try:
                major_version = int(node_version.split('.')[0])
                if major_version < 20:  # Node 20+ is recommended
                    issues.append({
                        "type": "nodejs",
                        "severity": "medium",
                        "description": f"Node.js version {node_version} is outdated",
                        "fix_command": "Visit https://nodejs.org/ for latest version"
                    })
            except (ValueError, IndexError):
                pass
        
        self.security_issues = issues
        self.logger.info(f"🚨 Found {len(issues)} security issues")
        return issues

    def apply_updates(self) -> List[Dict]:
        """Apply security updates automatically"""
        if not self.auto_update:
            self.logger.info("⏭️  Skipping updates (dry-run mode or auto-update disabled)")
            return []
            
        self.logger.info("🔧 Applying security updates...")
        applied = []
        
        for issue in self.security_issues:
            if issue['severity'] in ['critical', 'high']:
                command = issue['fix_command']
                
                # Skip macOS updates (require restart)
                if 'softwareupdate' in command:
                    self.logger.info(f"⏭️  Skipping macOS update (requires manual restart): {issue['description']}")
                    continue
                
                self.logger.info(f"🔧 Applying fix: {command}")
                
                if not self.dry_run:
                    output, returncode = self.run_command(command)
                    if returncode == 0:
                        applied.append({
                            "issue": issue['description'],
                            "command": command,
                            "status": "success",
                            "output": output[:500]  # Truncate long output
                        })
                        self.logger.info(f"✅ Successfully applied: {issue['description']}")
                    else:
                        applied.append({
                            "issue": issue['description'],
                            "command": command,
                            "status": "failed",
                            "output": output[:500]
                        })
                        self.logger.error(f"❌ Failed to apply: {issue['description']}")
                else:
                    applied.append({
                        "issue": issue['description'],
                        "command": command,
                        "status": "dry_run",
                        "output": "Would run in live mode"
                    })
                    self.logger.info(f"🧪 Dry run: {command}")
        
        self.updates_applied = applied
        return applied

    def generate_reports(self):
        """Generate comprehensive reports"""
        self.logger.info("📊 Generating reports...")
        
        # Markdown report
        md_file = self.output_dir / f"security_audit_report_{self.timestamp}.md"
        with open(md_file, 'w') as f:
            f.write(f"# Mac Security Audit Report\n\n")
            f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Mode:** {'Dry Run' if self.dry_run else 'Live Update' if self.auto_update else 'Analysis Only'}\n\n")
            
            # Software Inventory Summary
            f.write("## Software Inventory Summary\n\n")
            total_items = 0
            for category, items in self.inventory.items():
                count = len(items)
                total_items += count
                f.write(f"- **{category.replace('_', ' ').title()}**: {count} items\n")
            f.write(f"- **Total Software Items**: {total_items}\n\n")
            
            # Security Issues
            f.write("## Security Issues Found\n\n")
            if not self.security_issues:
                f.write("✅ No critical security issues found!\n\n")
            else:
                critical = [i for i in self.security_issues if i['severity'] == 'critical']
                high = [i for i in self.security_issues if i['severity'] == 'high']
                medium = [i for i in self.security_issues if i['severity'] == 'medium']
                
                if critical:
                    f.write("### 🔴 Critical Issues\n")
                    for issue in critical:
                        f.write(f"- **{issue['description']}**\n")
                        f.write(f"  - Fix: `{issue['fix_command']}`\n\n")
                
                if high:
                    f.write("### 🟡 High Priority Issues\n")
                    for issue in high:
                        f.write(f"- **{issue['description']}**\n")
                        f.write(f"  - Fix: `{issue['fix_command']}`\n\n")
                
                if medium:
                    f.write("### 🟢 Medium Priority Issues\n")
                    for issue in medium:
                        f.write(f"- **{issue['description']}**\n")
                        f.write(f"  - Fix: `{issue['fix_command']}`\n\n")
            
            # Updates Applied
            if self.updates_applied:
                f.write("## Updates Applied\n\n")
                for update in self.updates_applied:
                    status_icon = "✅" if update['status'] == 'success' else "❌" if update['status'] == 'failed' else "🧪"
                    f.write(f"- {status_icon} **{update['issue']}**\n")
                    f.write(f"  - Command: `{update['command']}`\n")
                    f.write(f"  - Status: {update['status']}\n\n")
        
        # JSON report for programmatic use
        json_file = self.output_dir / f"security_audit_data_{self.timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({
                "timestamp": self.timestamp,
                "mode": "dry_run" if self.dry_run else "live" if self.auto_update else "analysis",
                "inventory": self.inventory,
                "security_issues": self.security_issues,
                "updates_applied": self.updates_applied,
                "summary": {
                    "total_software_items": sum(len(v) for v in self.inventory.values()),
                    "security_issues_found": len(self.security_issues),
                    "critical_issues": len([i for i in self.security_issues if i['severity'] == 'critical']),
                    "updates_applied": len(self.updates_applied)
                }
            }, f, indent=2)
        
        self.logger.info(f"📊 Reports generated:")
        self.logger.info(f"  - Markdown: {md_file}")
        self.logger.info(f"  - JSON: {json_file}")

    def run_full_audit(self):
        """Run complete security audit process"""
        self.logger.info("🚀 Starting Mac Security Audit...")
        
        try:
            # Step 1: Inventory software
            self.inventory_applications()
            
            # Step 2: Check security issues
            self.check_security_issues()
            
            # Step 3: Apply updates if requested
            if self.auto_update or self.dry_run:
                self.apply_updates()
            
            # Step 4: Generate reports
            self.generate_reports()
            
            # Summary
            total_items = sum(len(v) for v in self.inventory.values())
            issues_count = len(self.security_issues)
            critical_count = len([i for i in self.security_issues if i['severity'] == 'critical'])
            
            self.logger.info("=" * 60)
            self.logger.info("🎯 AUDIT COMPLETE")
            self.logger.info(f"📦 Total software items: {total_items}")
            self.logger.info(f"🚨 Security issues found: {issues_count}")
            self.logger.info(f"🔴 Critical issues: {critical_count}")
            self.logger.info(f"🔧 Updates applied: {len(self.updates_applied)}")
            self.logger.info("📊 Check the generated reports for detailed information")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"❌ Audit failed: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Mac Security Audit Script")
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory for reports")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show what would be updated without applying changes")
    parser.add_argument("--auto-update", "-u", action="store_true", help="Automatically apply security updates")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create auditor and run
    auditor = MacSecurityAuditor(
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        auto_update=args.auto_update
    )
    
    auditor.run_full_audit()

if __name__ == "__main__":
    main()