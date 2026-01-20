/**
 * Wizard Controller for JobForge Demo
 *
 * Manages 4-step wizard navigation with accessibility features
 * including focus management and screen reader announcements.
 */

class WizardController {
  /**
   * Create a WizardController instance.
   */
  constructor() {
    this.currentStep = 1;
    this.totalSteps = 4;
    this.steps = document.querySelectorAll('.wizard-step');
    this.progressItems = document.querySelectorAll('.wizard-progress .step');
    this.announcer = document.getElementById('announcements');

    // Step completion state
    this.completedSteps = new Set();

    // Initialize keyboard navigation
    this.initKeyboardNav();
  }

  /**
   * Navigate to a specific step.
   * @param {number} stepNumber - Step number (1-4)
   * @returns {boolean} Whether navigation succeeded
   */
  goToStep(stepNumber) {
    if (stepNumber < 1 || stepNumber > this.totalSteps) {
      return false;
    }

    // Don't allow jumping ahead without completing previous steps
    if (stepNumber > this.currentStep + 1 && !this.completedSteps.has(stepNumber - 1)) {
      return false;
    }

    // Update step visibility
    this.steps.forEach((step, index) => {
      const stepNum = index + 1;
      step.classList.toggle('active', stepNum === stepNumber);
      step.setAttribute('aria-hidden', stepNum !== stepNumber);
    });

    // Update progress indicators
    this.progressItems.forEach((item, index) => {
      const stepNum = index + 1;
      item.classList.toggle('active', stepNum === stepNumber);
      item.classList.toggle('completed', this.completedSteps.has(stepNum));
    });

    // Mark previous step as completed
    if (stepNumber > this.currentStep) {
      this.completedSteps.add(this.currentStep);
    }

    this.currentStep = stepNumber;

    // Focus management - move focus to step heading
    this.focusCurrentStep();

    // Announce step change to screen readers
    this.announceStepChange();

    // Update navigation buttons
    this.updateNavButtons();

    return true;
  }

  /**
   * Navigate to next step.
   * @returns {boolean} Whether navigation succeeded
   */
  next() {
    if (this.currentStep < this.totalSteps && this.canProceed()) {
      return this.goToStep(this.currentStep + 1);
    }
    return false;
  }

  /**
   * Navigate to previous step.
   * @returns {boolean} Whether navigation succeeded
   */
  previous() {
    if (this.currentStep > 1) {
      return this.goToStep(this.currentStep - 1);
    }
    return false;
  }

  /**
   * Check if user can proceed to next step.
   * Override validation logic per step as needed.
   * @returns {boolean}
   */
  canProceed() {
    switch (this.currentStep) {
      case 1:
        // Load step - always can proceed (will connect to SSE)
        return true;
      case 2:
        // Power BI step - can proceed when deployment narration completes
        return this.completedSteps.has(2) || this.isDeploymentComplete();
      case 3:
        // Review step - always can proceed
        return true;
      case 4:
        // Catalogue step - final step
        return false;
      default:
        return false;
    }
  }

  /**
   * Check if deployment narration is complete.
   * @returns {boolean}
   */
  isDeploymentComplete() {
    // Check for completion indicator in the UI
    const completionMessage = document.getElementById('completion-message');
    return completionMessage && completionMessage.classList.contains('visible');
  }

  /**
   * Mark a step as complete.
   * @param {number} stepNumber - Step number to mark complete
   */
  markComplete(stepNumber) {
    this.completedSteps.add(stepNumber);

    // Update progress indicator
    const progressItem = this.progressItems[stepNumber - 1];
    if (progressItem) {
      progressItem.classList.add('completed');
    }

    this.updateNavButtons();
  }

  /**
   * Focus the current step's first heading or interactive element.
   */
  focusCurrentStep() {
    const currentStepEl = this.steps[this.currentStep - 1];
    if (!currentStepEl) return;

    // Find the step heading
    const heading = currentStepEl.querySelector('h2');
    if (heading) {
      // Make heading focusable temporarily
      heading.setAttribute('tabindex', '-1');
      heading.focus();
      // Remove tabindex after focus (heading shouldn't be in tab order)
      setTimeout(() => heading.removeAttribute('tabindex'), 100);
    }
  }

  /**
   * Announce step change to screen readers.
   */
  announceStepChange() {
    if (!this.announcer) return;

    const stepNames = ['Load', 'Power BI', 'Review', 'Catalogue'];
    const message = `Step ${this.currentStep} of ${this.totalSteps}: ${stepNames[this.currentStep - 1]}`;

    this.announcer.textContent = message;
  }

  /**
   * Make a general announcement to screen readers.
   * @param {string} message - Message to announce
   */
  announce(message) {
    if (!this.announcer) return;
    this.announcer.textContent = message;
  }

  /**
   * Update navigation button states.
   */
  updateNavButtons() {
    const backButton = document.getElementById('back-button');
    const nextButton = document.getElementById('next-button');

    if (backButton) {
      backButton.disabled = this.currentStep === 1;
    }

    if (nextButton) {
      // Hide next button on last step, disable if can't proceed
      if (this.currentStep === this.totalSteps) {
        nextButton.style.visibility = 'hidden';
      } else {
        nextButton.style.visibility = 'visible';
        nextButton.disabled = !this.canProceed();
      }
    }
  }

  /**
   * Initialize keyboard navigation.
   */
  initKeyboardNav() {
    document.addEventListener('keydown', (e) => {
      // Enter on buttons already handled by browser
      // Escape - could cancel current operation if applicable

      // Arrow keys for progress navigation (optional accessibility feature)
      if (e.target.closest('.wizard-progress')) {
        if (e.key === 'ArrowRight') {
          e.preventDefault();
          const nextStep = Math.min(this.currentStep + 1, this.totalSteps);
          if (this.completedSteps.has(nextStep - 1) || nextStep === this.currentStep + 1) {
            this.goToStep(nextStep);
          }
        } else if (e.key === 'ArrowLeft') {
          e.preventDefault();
          this.previous();
        }
      }
    });
  }

  /**
   * Get current step number.
   * @returns {number}
   */
  getCurrentStep() {
    return this.currentStep;
  }

  /**
   * Reset wizard to initial state.
   */
  reset() {
    this.completedSteps.clear();
    this.goToStep(1);
  }
}

// Export for use in main.js
window.WizardController = WizardController;
