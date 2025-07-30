# Mac Security Audit Script

Comprehensive automated security audit tool for macOS that inventories software, identifies security vulnerabilities, and applies updates automatically.

## 🚀 Quick Start

```bash
# Check for security issues only
./run_security_audit.sh check

# Preview what would be updated (safe)
./run_security_audit.sh dry-run

# Apply security updates automatically
./run_security_audit.sh update

# Full detailed audit with inventory
./run_security_audit.sh full-report
```

## 📋 What It Does

### 1. **Software Inventory**
- ✅ User Applications (/Applications)
- ✅ System Applications (/System/Applications)  
- ✅ System Utilities
- ✅ Homebrew packages
- ✅ AI Models (Ollama)
- ✅ Python packages (pip)
- ✅ Node.js packages (npm)
- ✅ Command line tools

### 2. **Security Vulnerability Detection**
- 🔴 **Critical**: Severely outdated pip, major system vulnerabilities
- 🟡 **High**: Security-relevant packages (lxml, requests, openssl, etc.)
- 🟢 **Medium**: General package updates, Node.js version checks
- 🔍 **System Updates**: macOS security patches

### 3. **Automated Updates**
- **Safe Updates**: Python packages, pip, minor security patches
- **Manual Review**: macOS system updates (require restart)
- **Dependency Checking**: Validates updates before applying
- **Rollback Info**: Logs all changes for troubleshooting

## 🛠️ Installation & Setup

1. **Download the scripts**:
   ```bash
   # The scripts are already in your current directory
   ls -la security_audit_script.py run_security_audit.sh
   ```

2. **Make executable** (already done):
   ```bash
   chmod +x security_audit_script.py run_security_audit.sh
   ```

3. **Run your first audit**:
   ```bash
   ./run_security_audit.sh check
   ```

## 📖 Usage Examples

### Basic Security Check
```bash
./run_security_audit.sh check
```
- Lists all security issues found
- No changes applied
- Generates basic report

### Preview Updates (Recommended)
```bash
./run_security_audit.sh dry-run
```
- Shows exactly what would be updated
- Safe to run - makes no changes
- Perfect for testing

### Apply Security Updates
```bash
./run_security_audit.sh update
```
- **⚠️ Warning**: This applies real changes
- Updates critical security packages
- Skips system updates that require restart
- Creates backup logs

### Complete Audit with Detailed Inventory
```bash
./run_security_audit.sh full-report
```
- Complete software inventory
- Detailed security analysis
- Comprehensive markdown + JSON reports
- Verbose logging

## 📊 Output Files

Each run generates timestamped files:

- **`security_audit_report_YYYYMMDD_HHMMSS.md`** - Human-readable report
- **`security_audit_data_YYYYMMDD_HHMMSS.json`** - Machine-readable data
- **`security_audit_YYYYMMDD_HHMMSS.log`** - Detailed execution log

## 🔧 Advanced Usage

### Direct Python Script
```bash
# Analysis only
python3 security_audit_script.py

# Dry run with verbose logging
python3 security_audit_script.py --dry-run --verbose

# Auto-update with custom output directory
python3 security_audit_script.py --auto-update --output-dir ./reports
```

### Command Line Options
- `--dry-run, -d`: Show what would be updated without applying
- `--auto-update, -u`: Automatically apply security updates  
- `--output-dir, -o`: Specify output directory for reports
- `--verbose, -v`: Enable verbose logging

## 🔒 Security Features

### Safe by Design
- **Dry-run first**: Always test before applying changes
- **Critical-first**: Prioritizes most important security issues
- **No system changes**: Skips updates requiring restart/admin
- **Full logging**: Every action is logged for review

### Update Priority System
1. **Critical**: pip, major security vulnerabilities
2. **High**: lxml, requests, openssl, authentication packages  
3. **Medium**: General package updates
4. **Manual**: macOS system updates (flagged for manual review)

### Dependency Safety
- Validates package compatibility before updating
- Reports dependency conflicts
- Creates restoration commands in logs

## 🎯 Typical Workflow

1. **Weekly Check**: `./run_security_audit.sh check`
2. **Preview Updates**: `./run_security_audit.sh dry-run`  
3. **Apply Updates**: `./run_security_audit.sh update`
4. **Monthly Full Audit**: `./run_security_audit.sh full-report`

## ⚠️ Important Notes

### What Gets Updated Automatically
- ✅ Python pip and packages
- ✅ Security-critical Python libraries
- ✅ Some Homebrew packages

### What Requires Manual Action
- ❌ macOS system updates (require restart)
- ❌ Major version upgrades (breaking changes)
- ❌ Applications requiring GUI interaction

### Prerequisites
- Python 3.6+ (system default is fine)
- Standard macOS command line tools
- Optional: Homebrew, Node.js, Ollama for full inventory

## 🆘 Troubleshooting

### Permission Issues
```bash
# If script isn't executable
chmod +x security_audit_script.py run_security_audit.sh

# If pip install fails with permissions
python3 -m pip install --user --upgrade [package]
```

### Package Conflicts
Check the log file for dependency conflict details. Most conflicts are non-critical and can be resolved by updating related packages.

### Script Hangs
The script has 5-minute timeouts on all operations. If it hangs, check your internet connection or try running individual commands manually.

## 🔄 Automation

### Cron Job (Weekly Security Check)
```bash
# Add to crontab (crontab -e):
0 9 * * 1 cd /path/to/scripts && ./run_security_audit.sh check >> weekly_security.log 2>&1
```

### Launchd (macOS Native Scheduling)
Create a `.plist` file in `~/Library/LaunchAgents/` for native macOS automation.

---

## 📞 Support

This script was created by Claude (Anthropic AI Assistant) and covers the complete workflow you requested:

1. ✅ **Software Inventory**: Complete system scan
2. ✅ **Security Analysis**: Vulnerability detection  
3. ✅ **Automated Updates**: Safe security patching
4. ✅ **Comprehensive Reporting**: Markdown + JSON + logs

**Created**: 2025-07-30  
**Version**: 1.0  
**Tested on**: macOS Sequoia 15.x