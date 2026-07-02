#!/bin/bash
# Mac Security Audit Runner Script
# Provides easy-to-use interface for the Python security audit script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/security_audit_script.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo -e "${BLUE}Mac Security Audit Script${NC}"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  check           - Only check for security issues (default)"
    echo "  dry-run         - Show what would be updated without applying changes"
    echo "  update          - Apply security updates automatically"
    echo "  full-report     - Generate detailed software inventory + security check"
    echo "  --help          - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 check                    # Check for security issues only"
    echo "  $0 dry-run                  # See what would be updated"
    echo "  $0 update                   # Apply security updates"
    echo "  $0 full-report             # Complete audit with detailed inventory"
}

check_requirements() {
    echo -e "${BLUE}🔍 Checking requirements...${NC}"
    
    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 is required but not installed${NC}"
        exit 1
    fi
    
    # Check if script exists
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        echo -e "${RED}❌ Security audit script not found: $PYTHON_SCRIPT${NC}"
        exit 1
    fi
    
    # Make script executable
    chmod +x "$PYTHON_SCRIPT"
    
    echo -e "${GREEN}✅ Requirements check passed${NC}"
}

run_audit() {
    local mode="$1"
    local args=""
    
    case "$mode" in
        "check")
            echo -e "${YELLOW}🔒 Running security check only...${NC}"
            args=""
            ;;
        "dry-run")
            echo -e "${YELLOW}🧪 Running dry-run (no changes will be applied)...${NC}"
            args="--dry-run"
            ;;
        "update")
            echo -e "${RED}⚠️  Running with auto-update (changes will be applied)...${NC}"
            echo "Press Enter to continue or Ctrl+C to cancel..."
            read -r
            args="--auto-update"
            ;;
        "full-report")
            echo -e "${BLUE}📊 Running full audit with detailed reporting...${NC}"
            args="--verbose"
            ;;
        *)
            echo -e "${RED}❌ Unknown mode: $mode${NC}"
            print_usage
            exit 1
            ;;
    esac
    
    # Run the Python script
    python3 "$PYTHON_SCRIPT" $args
    
    echo ""
    echo -e "${GREEN}✅ Audit completed successfully!${NC}"
    echo -e "${BLUE}📋 Check the generated reports for detailed information:${NC}"
    ls -la security_audit_*.md security_audit_*.json security_audit_*.log 2>/dev/null | head -5
}

main() {
    echo -e "${BLUE}🛡️  Mac Security Audit Script${NC}"
    echo "======================================"
    
    # Check requirements
    check_requirements
    
    # Parse arguments
    mode="${1:-check}"
    
    if [ "$mode" = "--help" ] || [ "$mode" = "-h" ]; then
        print_usage
        exit 0
    fi
    
    # Run the audit
    run_audit "$mode"
    
    echo ""
    echo -e "${GREEN}🎯 Security audit complete!${NC}"
    echo -e "${BLUE}💡 Tip: Run '$0 --help' to see all available options${NC}"
}

# Run main function
main "$@"