<template>
    <button :class="buttonClasses" :disabled="disabled" @click="$emit('click', $event)">
        <component v-if="iconLeft" :is="iconLeft" class="icon-left" />
        <span class="button-content">
            <slot />
        </span>
        <div v-if="loading" class="loading-spinner"></div>
    </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface Props {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success' | 'warning'
    size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
    disabled?: boolean
    loading?: boolean
    iconLeft?: any
    iconRight?: any
    fullWidth?: boolean
}

const props = withDefaults(defineProps<Props>(), {
    variant: 'primary',
    size: 'md',
    disabled: false,
    loading: false,
    iconLeft: undefined,
    iconRight: undefined,
    fullWidth: false
})

defineEmits<{
    click: [event: Event]
}>()

const buttonClasses = computed(() => {
    const classes = [
        'base-button',
        `variant-${props.variant}`,
        `size-${props.size}`
    ]

    if (props.disabled || props.loading) {
        classes.push('disabled')
    }

    if (props.loading) {
        classes.push('loading')
    }

    if (props.fullWidth) {
        classes.push('full-width')
    }

    return classes.join(' ')
})
</script>

<style scoped>
.base-button {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    font-weight: 500;
    font-family: inherit;
    border: 1px solid transparent;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: all 0.2s ease;
    overflow: hidden;
    white-space: nowrap;
    text-decoration: none;
}

.button-content {
    display: flex;
    align-items: center;
    gap: inherit;
}

/* Base variants */
.variant-primary {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
    color: white;
    border-color: var(--color-primary);
    box-shadow: 0 2px 4px rgba(29, 78, 216, 0.2);
}

.variant-primary:hover:not(.disabled) {
    background: linear-gradient(135deg, var(--color-primary-hover) 0%, #1d4ed8 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(29, 78, 216, 0.3);
}

.variant-secondary {
    background-color: transparent;
    color: var(--color-text-primary);
    border-color: var(--color-border);
}

.variant-secondary:hover:not(.disabled) {
    background-color: rgba(29, 78, 216, 0.08);
    border-color: var(--color-primary);
    color: var(--color-primary);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(29, 78, 216, 0.15);
}

.variant-ghost {
    background-color: transparent;
    color: var(--color-text-primary);
    border-color: transparent;
}

.variant-ghost:hover:not(.disabled) {
    background-color: rgba(29, 78, 216, 0.05);
    border-color: rgba(29, 78, 216, 0.2);
    transform: translateY(-1px);
}

.variant-danger {
    background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
    color: white;
    border-color: #dc2626;
    box-shadow: 0 2px 4px rgba(220, 38, 38, 0.2);
}

.variant-danger:hover:not(.disabled) {
    background: linear-gradient(135deg, #b91c1c 0%, #991b1b 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.variant-success {
    background: linear-gradient(135deg, #059669 0%, #047857 100%);
    color: white;
    border-color: #059669;
    box-shadow: 0 2px 4px rgba(5, 150, 105, 0.2);
}

.variant-success:hover:not(.disabled) {
    background: linear-gradient(135deg, #047857 0%, #065f46 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
}

.variant-warning {
    background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
    color: white;
    border-color: #d97706;
    box-shadow: 0 2px 4px rgba(217, 119, 6, 0.2);
}

.variant-warning:hover:not(.disabled) {
    background: linear-gradient(135deg, #b45309 0%, #92400e 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(217, 119, 6, 0.3);
}

/* Sizes */
.size-xs {
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
    line-height: 1rem;
}

.size-sm {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
    line-height: 1.25rem;
}

.size-md {
    padding: 0.625rem 1.25rem;
    font-size: 0.875rem;
    line-height: 1.25rem;
}

.size-lg {
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    line-height: 1.5rem;
}

.size-xl {
    padding: 1rem 2rem;
    font-size: 1.125rem;
    line-height: 1.75rem;
}

/* Full width */
.full-width {
    width: 100%;
}

/* Disabled state */
.disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none !important;
    box-shadow: none !important;
}

/* Icon styling */
.icon-left {
    width: 1rem;
    height: 1rem;
    flex-shrink: 0;
}

.size-xs .icon-left {
    width: 0.75rem;
    height: 0.75rem;
}

.size-sm .icon-left {
    width: 0.875rem;
    height: 0.875rem;
}

.size-lg .icon-left {
    width: 1.125rem;
    height: 1.125rem;
}

.size-xl .icon-left {
    width: 1.25rem;
    height: 1.25rem;
}

/* Active state */
.base-button:active:not(.disabled) {
    transform: translateY(0);
}

/* Loading state */
.loading-spinner {
    width: 1rem;
    height: 1rem;
    border: 2px solid transparent;
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Shine effect for primary buttons */
.variant-primary::before,
.variant-danger::before,
.variant-success::before,
.variant-warning::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
}

.variant-primary:hover:not(.disabled)::before,
.variant-danger:hover:not(.disabled)::before,
.variant-success:hover:not(.disabled)::before,
.variant-warning:hover:not(.disabled)::before {
    left: 100%;
}

/* Focus styles */
.base-button:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
}
</style>