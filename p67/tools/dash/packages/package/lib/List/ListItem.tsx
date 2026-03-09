import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import { forwardRef } from 'react';

import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';

type ListItemProps<T extends keyof ReactHTML = 'li'> = SlottedContainerProps<T>;

const styles = stylex.create({
    listItem: {
        listStyle: {
            default: 'none',
            ':is(ol > li)': 'decimal',
            ":is(ul:not([data-unstyled-list='true']) > li)": 'disc',
        },
        margin: 0,
        padding: 0,
        paddingBottom: tokens['space-vertical-sm'],
        paddingTop: tokens['space-vertical-sm'],
    },
});

const ListItem = forwardRef<HTMLLIElement, ListItemProps>(
    (props, forwardedRef) => {
        return (
            <SlottedContainer
                {...props}
                tag="li"
                stylexProps={stylex.props(styles.listItem)}
                ref={forwardedRef}
            />
        );
    },
);

ListItem.displayName = 'List.Item';
export type { ListItemProps };
export { ListItem };
