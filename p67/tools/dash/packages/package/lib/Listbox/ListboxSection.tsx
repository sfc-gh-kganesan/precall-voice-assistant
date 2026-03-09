import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type React from 'react';
import { forwardRef, useContext } from 'react';
import { useId } from 'react-aria';
import {
    ListBoxItem,
    ListBoxSection as ReactAriaListBoxSection,
    Separator,
} from 'react-aria-components';

import { useDividerStyles } from '../Divider/useDividerStyles';
import { MenuSectionHeader } from '../Menu/MenuSectionHeader';
import { SizeContext } from '../main';

const styles = stylex.create({
    divider: {
        display: {
            // For un-virtualized listboxes
            ":is([role='listbox'] > [data-separator-section] > *)": 'none',
            // For virtualized listboxes
            ':is(:last-child > [data-separator-section] > *)': 'none',
        },
        marginBottom: 0,
        marginTop: 0,
    },
    small: {
        marginTop: tokens['space-vertical-3xs'],
    },
    header: {
        marginTop: tokens['space-vertical-sm'],
    },
    headerSmall: {
        marginTop: tokens['space-vertical-3xs'],
    },
});

/**
 * A component that renders a divider for a section.
 */
function SectionDivider({
    dividerKey,
}: {
    /**
     * The key of the divider.
     */
    dividerKey: string;
}) {
    const sizeContext = useContext(SizeContext);
    const baseDivider = useDividerStyles({ direction: 'horizontal' });
    const dividerStyles = stylex.props(
        baseDivider,
        styles.divider,
        sizeContext === 'small' && styles.small,
    );

    return (
        <ListBoxItem
            id={dividerKey}
            aria-label="Section divider"
            textValue="`"
            data-separator-section
            isDisabled
        >
            <Separator {...dividerStyles} />
        </ListBoxItem>
    );
}

interface ListboxSectionProps {
    /**
     * The children of the section.
     */
    children: React.ReactNode;
    /**
     * The label of the section.
     */
    label?: string | undefined;
}

const ListboxSection = forwardRef<HTMLAreaElement, ListboxSectionProps>(
    function ListboxSection({ children, label }, ref) {
        const dividerKey = useId();
        const sizeContext = useContext(SizeContext);

        return (
            <>
                <ReactAriaListBoxSection ref={ref}>
                    {label && (
                        <MenuSectionHeader
                            {...stylex.props(
                                styles.header,
                                sizeContext === 'small' && styles.headerSmall,
                            )}
                        >
                            {label}
                        </MenuSectionHeader>
                    )}
                    {children}
                </ReactAriaListBoxSection>
                <SectionDivider dividerKey={dividerKey} />
            </>
        );
    },
);

ListboxSection.displayName = 'Listbox.Section';

export type { ListboxSectionProps };
export { ListboxSection };
