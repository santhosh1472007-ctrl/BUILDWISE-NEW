// Modern UI Interactions and Micro-animations
document.addEventListener('DOMContentLoaded', function() {
  // Button ripple effect
  function createRipple(event) {
    const button = event.currentTarget;
    const circle = document.createElement('span');
    const diameter = Math.max(button.clientWidth, button.clientHeight);
    const radius = diameter / 2;

    const rect = button.getBoundingClientRect();
    circle.style.width = circle.style.height = diameter + 'px';
    circle.style.left = event.clientX - rect.left - radius + 'px';
    circle.style.top = event.clientY - rect.top - radius + 'px';
    circle.classList.add('ripple');

    const ripple = button.getElementsByClassName('ripple')[0];
    if (ripple) {
      ripple.remove();
    }

    button.appendChild(circle);
  }

  // Add ripple effect to buttons
  const buttons = document.querySelectorAll('.btn, .button');
  buttons.forEach(button => {
    button.addEventListener('click', createRipple);
  });

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  // Card hover animations
  const cards = document.querySelectorAll('.card, .module-card, .stat-card');
  cards.forEach(card => {
    card.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-4px) scale(1.02)';
    });

    card.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
    });
  });

  // Loading state for forms
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', function() {
      const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<div class="spinner"></div> Processing...';
      }
    });
  });

  // Auto-scroll to latest message in chat
  const messages = document.getElementById('messages');
  if (messages) {
    messages.scrollTop = messages.scrollHeight;
    
    // Observe new messages for auto-scroll
    const observer = new MutationObserver(() => {
      messages.scrollTop = messages.scrollHeight;
    });
    observer.observe(messages, { childList: true });
  }

  // Keyboard navigation improvements
  document.addEventListener('keydown', function(e) {
    // Close modals with Escape
    if (e.key === 'Escape') {
      const modals = document.querySelectorAll('.modal[style*="display: block"]');
      modals.forEach(modal => modal.style.display = 'none');
    }
  });

  // Focus management for accessibility
  const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Tab') {
      document.body.classList.add('keyboard-navigation');
    }
  });

  document.addEventListener('mousedown', function() {
    document.body.classList.remove('keyboard-navigation');
  });

  // Intersection Observer for fade-in animations
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
      }
    });
  }, observerOptions);

  // Observe elements for animation
  document.querySelectorAll('.module-card, .stat-card, .card').forEach(card => {
    observer.observe(card);
  });

  // Theme toggle (if needed in future)
  function toggleTheme() {
    document.body.classList.toggle('dark-theme');
    localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
  }

  // Load saved theme
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'dark') {
    document.body.classList.add('dark-theme');
  }

  // Voice interaction enhancements
  const voiceButtons = document.querySelectorAll('[data-voice]');
  voiceButtons.forEach(button => {
    button.addEventListener('click', function() {
      this.classList.add('listening');
      setTimeout(() => this.classList.remove('listening'), 3000);
    });
  });

  // Form validation feedback
  const inputs = document.querySelectorAll('input, textarea, select');
  inputs.forEach(input => {
    input.addEventListener('blur', function() {
      if (this.checkValidity()) {
        this.classList.remove('invalid');
        this.classList.add('valid');
      } else {
        this.classList.remove('valid');
        this.classList.add('invalid');
      }
    });
  });

  // Toast notifications system
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 	oast toast-;
    toast.innerHTML = 
      <div class="toast-content">
        <span class="toast-message"></span>
        <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
      </div>
    ;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('show');
    }, 100);

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 5000);
  }

  // Make showToast globally available
  window.showToast = showToast;

  // Loading states for async operations
  window.showLoading = function(element) {
    element.classList.add('loading');
    element.setAttribute('aria-busy', 'true');
  };

  window.hideLoading = function(element) {
    element.classList.remove('loading');
    element.setAttribute('aria-busy', 'false');
  };
});

// CSS for ripple effect
const style = document.createElement('style');
style.textContent = 
  .ripple {
    position: absolute;
    border-radius: 50%;
    background-color: rgba(255, 255, 255, 0.6);
    transform: scale(0);
    animation: ripple 0.6s linear;
    pointer-events: none;
  }

  @keyframes ripple {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }

  .btn, .button {
    position: relative;
    overflow: hidden;
  }

  .animate-in {
    animation: fadeInUp 0.6s ease-out;
  }

  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(30px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .listening {
    animation: pulse 1.5s infinite;
  }

  .toast {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
    min-width: 300px;
    max-width: 500px;
    padding: 0;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-xl);
    transform: translateX(100%);
    transition: transform 0.3s ease;
  }

  .toast.show {
    transform: translateX(0);
  }

  .toast-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-md);
  }

  .toast-info {
    background: var(--accent-primary);
    color: white;
  }

  .toast-success {
    background: var(--status-online);
    color: white;
  }

  .toast-error {
    background: var(--status-offline);
    color: white;
  }

  .toast-close {
    background: none;
    border: none;
    color: inherit;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0;
    margin-left: var(--spacing-md);
  }

  .loading {
    position: relative;
    pointer-events: none;
  }

  .loading::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 20px;
    height: 20px;
    margin: -10px 0 0 -10px;
    border: 2px solid var(--border-primary);
    border-top: 2px solid var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .keyboard-navigation .btn:focus,
  .keyboard-navigation .site-nav a:focus {
    outline: 2px solid var(--accent-primary);
    outline-offset: 2px;
  }

  @media (prefers-reduced-motion: reduce) {
    .ripple, .animate-in, .listening, .toast {
      animation: none !important;
    }
  }
;
document.head.appendChild(style);
