import os
import subprocess
from datetime import datetime

# Global flag to ensure banner is only shown once
_banner_shown = False

def get_git_info():
    """Get git commit hash and build timestamp"""
    try:
        # Get git commit hash
        git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                         stderr=subprocess.DEVNULL).decode().strip()[:8]

        # Get git commit date
        git_date = subprocess.check_output(['git', 'show', '-s', '--format=%ci', 'HEAD'],
                                         stderr=subprocess.DEVNULL).decode().strip()

        return git_hash, git_date
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown", "unknown"

def get_build_info():
    """Get build information from environment or labels"""
    # Try to get from environment (set during Docker build)
    build_time = os.environ.get('BUILD_TIME')
    git_hash_env = os.environ.get('GIT_HASH')

    if build_time is None:
        # Fallback to current time for development
        build_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    return build_time, git_hash_env

def print_startup_banner():
    """Print a nice startup banner with application info"""
    global _banner_shown

    # Only show banner once
    if _banner_shown:
        return
    _banner_shown = True

    git_hash, git_date = get_git_info()
    build_time, git_hash_env = get_build_info()

    # Use environment git hash if available (from Docker build), otherwise git command
    display_hash = git_hash_env[:8] if git_hash_env else git_hash

    # ASCII art for "SMS-TICKETS"
    banner = r"""
                         _   _      _        _
 ___ _ __ ___  ___      | |_(_) ___| | _____| |_ ___
/ __| '_ ` _ \/ __|_____| __| |/ __| |/ / _ \ __/ __|
\__ \ | | | | \__ \_____| |_| | (__|   <  __/ |_\__ \
|___/_| |_| |_|___/      \__|_|\___|_|\_\___|\__|___/
    """

    print("\033[96m" + banner + "\033[0m")  # Cyan color
    print("\033[94m" + "="*70 + "\033[0m")  # Blue separator
    print(f"\033[92m🛠️  Build Info:\033[0m")
    print(f"   📅 Build Time: {build_time}")
    print(f"   🔗 Git Hash:   {display_hash}")
    if git_date != "unknown":
        print(f"   📝 Git Date:   {git_date}")
    print("\033[94m" + "="*70 + "\033[0m")
    print(f"\033[93m🚀 Starting Skate Sharpening Ticket System...\033[0m")
    print()
