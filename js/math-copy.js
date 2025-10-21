/**
 * Math Formula Copy and Display Functionality
 * Enables copying mathematical formulas and showing formula source on click
 */

document.addEventListener('DOMContentLoaded', function () {
    initMathCopy();

    // Watch for route changes in SPA
    let currentLocation = location.pathname;
    const observer = new MutationObserver(function () {
        if (location.pathname !== currentLocation) {
            currentLocation = location.pathname;
            setTimeout(initMathCopy, 500);
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

function initMathCopy() {
    const mathElements = document.querySelectorAll('semantics:not([data-copy-ready])');

    mathElements.forEach(function (element) {
        element.setAttribute('data-copy-ready', 'true');
        element.setAttribute('tabindex', '0');
        element.setAttribute('role', 'button');
        element.setAttribute('aria-label', 'Click to show/copy formula');
        element.style.cursor = 'pointer';

        // Find parent katex element
        const katexElement = element.closest('.katex');
        
        element.addEventListener('click', function(e) {
            handleMathClick.call(this, e, katexElement);
        });
        
        element.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleMathClick.call(this, e, katexElement);
            }
        });
    });

    // Close formula display when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.katex')) {
            const activeFormulas = document.querySelectorAll('.katex.show-formula');
            activeFormulas.forEach(function(element) {
                element.classList.remove('show-formula');
            });
        }
    });
}

function handleMathClick(event, katexElement) {
    event.preventDefault();
    event.stopPropagation();

    if (katexElement) {
        // Toggle formula display
        if (katexElement.classList.contains('show-formula')) {
            // If already showing, copy to clipboard
            const element = this;
            let textToCopy = '';

            const annotation = element.querySelector('annotation');
            if (annotation) {
                textToCopy = annotation.textContent.trim();
            } else {
                textToCopy = element.textContent.trim();
            }

            copyToClipboard(textToCopy, element);
            katexElement.classList.remove('show-formula');
        } else {
            // Hide other formulas first
            const activeFormulas = document.querySelectorAll('.katex.show-formula');
            activeFormulas.forEach(function(element) {
                element.classList.remove('show-formula');
            });
            
            // Show this formula
            katexElement.classList.add('show-formula');
        }
    }
}

function handleMathCopy(event) {
    event.preventDefault();
    event.stopPropagation();

    const element = this;
    let textToCopy = '';

    const annotation = element.querySelector('annotation');
    if (annotation) {
        textToCopy = annotation.textContent.trim();
    } else {
        textToCopy = element.textContent.trim();
    }

    copyToClipboard(textToCopy, element);
}

function copyToClipboard(text, element) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function () {
            showCopiedFeedback(element);
        }).catch(function (err) {
            console.error('Failed to copy:', err);
            fallbackCopy(text, element);
        });
    } else {
        fallbackCopy(text, element);
    }
}

function fallbackCopy(text, element) {
    try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);

        if (successful) {
            showCopiedFeedback(element);
        } else {
            showErrorFeedback(element);
        }
    } catch (err) {
        console.error('Failed to copy formula:', err);
        showErrorFeedback(element);
    }
}

function showCopiedFeedback(element) {
    element.classList.add('copying');
    element.classList.add('copied');

    setTimeout(function () {
        element.classList.remove('copying');
    }, 300);

    setTimeout(function () {
        element.classList.remove('copied');
    }, 2000);
}

function showErrorFeedback(element) {
    const originalBorder = element.style.borderColor;
    const originalBg = element.style.backgroundColor;

    element.style.borderColor = 'var(--ifm-color-danger)';
    element.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';

    setTimeout(function () {
        element.style.borderColor = originalBorder;
        element.style.backgroundColor = originalBg;
    }, 2000);
} 