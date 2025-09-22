import yaml
from pathlib import Path
from flask import request, g, current_app

# Cache for translations
_translations_cache = {}
_translation_file_times = {}

def load_translations():
    """Load translations from YAML files with hot-reloading in debug mode"""
    global _translations_cache

    # In production, use cached translations
    if not current_app.debug and _translations_cache:
        return _translations_cache

    # Check if any translation files have been modified
    reload_needed = False
    for lang in ['da', 'en']:
        file_path = f'translations/{lang}.yaml'
        try:
            current_mtime = Path(file_path).stat().st_mtime
            if (file_path not in _translation_file_times or
                    _translation_file_times[file_path] != current_mtime):
                _translation_file_times[file_path] = current_mtime
                reload_needed = True
        except FileNotFoundError:
            continue

    # Reload translations if files changed or cache is empty
    if reload_needed or not _translations_cache:
        print("[Translations] Reloading language files...")
        translations = {}
        for lang in ['da', 'en']:
            try:
                with open(f'translations/{lang}.yaml', 'r', encoding='utf-8') as f:
                    translations[lang] = yaml.safe_load(f)
            except FileNotFoundError:
                print(f"Warning: Translation file translations/{lang}.yaml not found")
                translations[lang] = {}
        _translations_cache = translations

    return _translations_cache

def get_translations():
    """Get current translations (with hot-reloading in debug mode)"""
    return load_translations()

def get_language():
    """Detect language from Accept-Language header"""
    if hasattr(g, 'language'):
        return g.language

    # Check Accept-Language header
    accept_lang = request.headers.get('Accept-Language', '').lower()

    # Nordic languages use Danish
    nordic_codes = ['da', 'dk', 'sv', 'se', 'no', 'nb', 'nn']
    if any(code in accept_lang for code in nordic_codes):
        g.language = 'da'
    else:
        g.language = 'en'

    return g.language

def t(key, *args, **kwargs):
    """Translate key to current language"""
    lang = get_language()
    translations = get_translations()
    translation = translations.get(lang, {}).get(key, translations.get('en', {}).get(key, key))

    # Handle string formatting
    if args or kwargs:
        try:
            if kwargs:
                return translation.format(**kwargs)
            else:
                return translation.format(*args)
        except Exception as e:
            print(f"Warning: Translation formatting error for key '{key}': {e}")
            return translation

    return translation