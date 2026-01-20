/**
 * Internationalization (i18n) module for JobForge Demo
 *
 * Provides bilingual EN/FR support with localStorage persistence.
 * Applies translations to elements with data-i18n attributes.
 */

class I18n {
  /**
   * Create an I18n instance.
   * Initializes with locale from localStorage or defaults to 'en'.
   */
  constructor() {
    this.locale = localStorage.getItem('jobforge-locale') || 'en';
    this.strings = {};
  }

  /**
   * Load locale strings from JSON file.
   * @param {string} locale - Locale code ('en' or 'fr')
   * @returns {Promise<void>}
   */
  async load(locale) {
    try {
      const response = await fetch(`locales/${locale}.json`);
      if (!response.ok) {
        throw new Error(`Failed to load locale: ${locale}`);
      }
      this.strings = await response.json();
      this.locale = locale;
      localStorage.setItem('jobforge-locale', locale);
      document.documentElement.lang = locale;
      this.apply();
    } catch (error) {
      console.error('I18n load error:', error);
      // Fall back to English if French fails
      if (locale !== 'en') {
        await this.load('en');
      }
    }
  }

  /**
   * Get translated string by dot-notation key.
   * @param {string} key - Translation key (e.g., 'step.load')
   * @returns {string} Translated string or key if not found
   */
  t(key) {
    const parts = key.split('.');
    let value = this.strings;

    for (const part of parts) {
      if (value && typeof value === 'object' && part in value) {
        value = value[part];
      } else {
        console.warn(`Translation missing: ${key}`);
        return key;
      }
    }

    return typeof value === 'string' ? value : key;
  }

  /**
   * Apply translations to all elements with data-i18n attributes.
   * Also handles data-i18n-aria for aria-label attributes.
   */
  apply() {
    // Apply text content translations
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(el => {
      const key = el.getAttribute('data-i18n');
      const translation = this.t(key);
      if (translation !== key) {
        el.textContent = translation;
      }
    });

    // Apply aria-label translations
    const ariaElements = document.querySelectorAll('[data-i18n-aria]');
    ariaElements.forEach(el => {
      const key = el.getAttribute('data-i18n-aria');
      const translation = this.t(key);
      if (translation !== key) {
        el.setAttribute('aria-label', translation);
      }
    });

    // Update page title
    const titleEl = document.querySelector('title');
    if (titleEl && titleEl.hasAttribute('data-i18n')) {
      const key = titleEl.getAttribute('data-i18n');
      const translation = this.t(key);
      if (translation !== key) {
        document.title = translation;
      }
    }
  }

  /**
   * Toggle between EN and FR locales.
   * @returns {Promise<string>} New locale code
   */
  async toggle() {
    const newLocale = this.locale === 'en' ? 'fr' : 'en';
    await this.load(newLocale);
    return newLocale;
  }

  /**
   * Get current locale.
   * @returns {string} Current locale code
   */
  getLocale() {
    return this.locale;
  }

  /**
   * Check if current locale is French.
   * @returns {boolean}
   */
  isFrench() {
    return this.locale === 'fr';
  }
}

// Export for use in main.js
window.I18n = I18n;
