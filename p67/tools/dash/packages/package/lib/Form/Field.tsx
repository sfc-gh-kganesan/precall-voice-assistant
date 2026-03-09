import { InfoCircleIcon } from '@snowflake/stellar-icons';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { HTMLAttributes } from 'react';
import { forwardRef, useContext, useMemo } from 'react';
import { IconButton } from '../Button';
import { Flex } from '../Layout/Flex';
import { Popover } from '../Popover';
import { Label, Paragraph } from '../Text';
import { FieldContext, FormContext, generateFieldId } from './FormContext';

interface FieldProps extends HTMLAttributes<HTMLDivElement> {
    /**
     * The id of the field.
     */
    id?: string | undefined;
    /**
     * The label of the field.
     */
    label: string;
    /**
     * Whether to show the label of the field.
     */
    showLabel?: boolean | undefined;
    /**
     * The description of the field.
     */
    description?: string | undefined;
    /**
     * Whether the field is in a success state.
     */
    success?: boolean | undefined;
    /**
     * Whether the field is in a warning state.
     */
    warning?: boolean | undefined;
    /**
     * Whether the field is in a error state.
     */
    error?: boolean | undefined;
    /**
     * The content of the info popover.
     */
    infoPopoverContent?: React.ReactNode | undefined;
}

const styles = stylex.create({
    container: {
        display: 'inline-flex',
        gap: tokens['space-gap-lg'] /* 16 */,
    },
    // Styles used when placed within a FieldSet.
    fieldSetContainer: {
        display: 'flex',
        gap: {
            default: tokens['space-gap-sm'] /* 8 */,
            '@container (width <= 480px)': tokens['space-gap-sm'],
        },
    },
    fieldSetContainerResponsive: {
        flexDirection: {
            default: 'row',
            '@container (width <= 480px)': 'column',
        },
    },
    fieldSetContainerColumn: {
        flexDirection: 'column',
    },
    fieldSetContainerRow: {
        flexDirection: 'row',
    },
    fieldSetControl: {
        flexBasis: '0%',
        flexGrow: 2,
    },
    fieldSetControlResponsive: {
        flexBasis: '0%',
        flexGrow: {
            default: 2, // maintains a 2:1 ratio with label in horizontal layout
            '@container (width <= 480px)': 'initial',
        },
    },
    fieldSetLabel: {
        flexBasis: '0%',
        flexGrow: 1,
    },
    fieldSetLabelResponsive: {
        flexBasis: '0%',
        flexGrow: {
            default: 1, // maintains a 1:2 ratio with control in horizontal layout

            '@container (width <= 480px)': 'initial',
        },
    },
    infoIconButton: {
        marginBlockEnd: -4, // Center the info icon button with the label without affecting the overall layout/height/spacing.
        marginBlockStart: -4, // TODO(SNOW-2349056): Remove this workaround when we do the spacing refactor.
    },
});

const Field = forwardRef<HTMLDivElement, FieldProps>((props, forwardedRef) => {
    const {
        id,
        label,
        showLabel = true,
        description,
        success,
        warning,
        error,
        infoPopoverContent,
        children,
        ...otherProps
    } = props;

    const formContext = useContext(FormContext);
    const inputId = useMemo(() => id ?? generateFieldId(), [id]);
    const labelId = useMemo(() => generateFieldId(), []);
    const descriptionId = useMemo(() => generateFieldId(), []);
    const hasFormContext = !!formContext;
    const isResponsive = hasFormContext && !formContext?.fieldFlexDirection;

    return (
        <FieldContext.Provider
            value={{
                label,
                showLabel,
                inputId: showLabel ? inputId : undefined,
                labelId,
                descriptionId: description ? descriptionId : undefined,
                success,
                warning,
                error,
            }}
        >
            <div
                {...otherProps}
                {...stylex.props(
                    styles.container,
                    hasFormContext && styles.fieldSetContainer,
                    isResponsive && styles.fieldSetContainerResponsive,
                    formContext?.fieldFlexDirection === 'column' &&
                        styles.fieldSetContainerColumn,
                    formContext?.fieldFlexDirection === 'row' &&
                        styles.fieldSetContainerRow,
                )}
                ref={forwardedRef}
            >
                {showLabel && (
                    <Flex
                        direction="row"
                        gap="0x"
                        align="start"
                        {...stylex.props(
                            hasFormContext && styles.fieldSetLabel,
                            isResponsive && styles.fieldSetLabelResponsive,
                        )}
                    >
                        <Label id={labelId}>{label}</Label>
                        {infoPopoverContent && (
                            <Popover
                                showArrow
                                trigger={
                                    <IconButton
                                        variant="tertiary"
                                        size="small"
                                        icon={InfoCircleIcon}
                                        aria-labelledby={labelId}
                                        {...stylex.props(styles.infoIconButton)}
                                    />
                                }
                                aria-labelledby={labelId}
                            >
                                {infoPopoverContent}
                            </Popover>
                        )}
                    </Flex>
                )}
                <Flex
                    direction="column"
                    grow={hasFormContext ? undefined : 1}
                    gap="0_5x"
                    {...stylex.props(
                        hasFormContext && styles.fieldSetControl,
                        isResponsive && styles.fieldSetControlResponsive,
                    )}
                >
                    {children}
                    {description && (
                        <Paragraph
                            variant={
                                error
                                    ? 'critical'
                                    : warning
                                      ? 'caution'
                                      : 'secondary'
                            }
                            size="small"
                            id={descriptionId}
                        >
                            {description}
                        </Paragraph>
                    )}
                </Flex>
            </div>
        </FieldContext.Provider>
    );
});

Field.displayName = 'Field';
export type { FieldProps };
export { Field };
