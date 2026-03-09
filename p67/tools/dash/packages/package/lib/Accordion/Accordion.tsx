import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { AriaAttributes, ReactHTML } from 'react';
import { forwardRef, useMemo } from 'react';
import { DisclosureGroup } from 'react-aria-components';
import { useMergedStyles } from '../hooks';
import type { Direction } from '../types';
import type { ControlledValueComponent } from '../util/Controlled';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { AccordionContent } from './AccordionContent';
import { AccordionItem } from './AccordionItem';
import { AccordionTrigger } from './AccordionTrigger';

/**
 * Converts a string or string array to a set of strings.
 */
function toSet(value: string | string[] | undefined): Set<string> | undefined {
    if (!value) return undefined;
    return new Set(typeof value === 'string' ? [value] : value);
}

type AccordionSlottedContainerProps<T extends keyof ReactHTML> = Omit<
    SlottedContainerProps<T>,
    'defaultValue' | 'dir'
>;
interface AccordionSingleProps<T extends keyof ReactHTML>
    extends AccordionImplProps<string>,
        AccordionSlottedContainerProps<T> {
    /**
     * The variant of the accordion.
     */
    variant: 'single';
    /**
     * Whether the accordion is collapsible.
     */
    collapsible?: boolean | undefined;
}
interface AccordionMultipleProps<T extends keyof ReactHTML>
    extends AccordionImplProps<string[]>,
        AccordionSlottedContainerProps<T> {
    /**
     * The variant of the accordion.
     */
    variant: 'multiple';
}
interface AccordionImplProps<V extends string | string[]>
    extends ControlledValueComponent<V> {
    /**
     * The variant of the accordion.
     */
    variant: 'single' | 'multiple';
    /**
     * Whether or not an accordion is disabled from user interaction.
     * @default false
     */
    disabled?: boolean | undefined;
    /**
     * The layout in which the Accordion operates.
     * @default vertical
     */
    orientation?: AriaAttributes['aria-orientation'] | undefined;
    /**
     * The language read direction.
     */
    dir?: Direction | undefined;
}

const styles = stylex.create({
    accordion: {
        backgroundColor: baltoTheme.surfaceLevel_2Background,
        borderRadius: 0,
        borderTopLeftRadius: {
            default: 'inherit',
            ':first-of-type': tokens['radius-sm'],
        },
        borderTopRightRadius: {
            default: 'inherit',
            ':first-of-type': tokens['radius-sm'],
        },
        display: 'flex',
        flexDirection: 'column',
        flexGrow: 1,
        gap: 0,

        borderBottomLeftRadius: {
            default: 'inherit',
            ':last-of-type': tokens['radius-sm'],
        },
        borderBottomRightRadius: {
            default: 'inherit',
            ':last-of-type': tokens['radius-sm'],
        },
    },
});

type AccordionProps<T extends keyof ReactHTML> =
    | AccordionSingleProps<T>
    | AccordionMultipleProps<T>;

const Root = forwardRef<HTMLDivElement, AccordionProps<'div'>>(
    (props, forwardedRef) => {
        const {
            variant,
            className,
            style,
            disabled,
            defaultValue,
            value,
            onValueChange,
            ...otherProps
        } = props;

        const stylexProps = useMergedStyles(
            className,
            style,
            stylex.props(styles.accordion),
        );

        const expandedKeys = useMemo(() => toSet(value), [value]);
        const defaultExpandedKeys = useMemo(
            () => toSet(defaultValue),
            [defaultValue],
        );

        return (
            <DisclosureGroup
                {...otherProps}
                {...stylexProps}
                allowsMultipleExpanded={variant === 'multiple'}
                isDisabled={disabled}
                ref={forwardedRef}
                defaultExpandedKeys={defaultExpandedKeys}
                expandedKeys={expandedKeys}
                onExpandedChange={(keySet) => {
                    const keys = Array.from(keySet);

                    if (variant === 'multiple') {
                        onValueChange?.(keys as string[], undefined);
                    } else {
                        onValueChange?.(keys[0] as string, undefined);
                    }
                }}
            />
        );
    },
);

Root.displayName = 'Accordion.Root';

export type { AccordionContentProps } from './AccordionContent';
export type { AccordionItemProps } from './AccordionItem';
export type { AccordionTriggerProps } from './AccordionTrigger';
export type { AccordionSingleProps, AccordionMultipleProps, AccordionProps };

export {
    Root,
    AccordionContent as Content,
    AccordionItem as Item,
    AccordionTrigger as Trigger,
};
