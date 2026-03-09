import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import { forwardedRefGeneric } from '../internal/utils/forwardRefGeneric';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import { ListItem } from './ListItem';

type ListTypeType = 'unordered' | 'ordered' | 'none';

interface ListProps<T extends ListTypeType>
    extends SlottedContainerProps<T extends 'unordered' ? 'ul' : 'ol'> {
    /**
     * The type of the list.
     * @default "none"
     */
    type?: T | undefined;
}

const styles = stylex.create({
    list: {
        display: 'flex',
        flexDirection: 'column',
        listStyle: 'none',
        margin: 0,
        padding: 0,
        paddingLeft: {
            ":not([data-unstyled-list='true'])": tokens['space-horizontal-3xl'],
        },
    },
});

const ListComponent = forwardedRefGeneric(
    <T extends ListTypeType>(
        { type: typeProp, ...props }: ListProps<T>,
        forwardedRef: React.Ref<HTMLUListElement | HTMLOListElement>,
    ) => {
        const type = typeProp ?? 'none';

        return (
            <SlottedContainer
                {...props}
                tag={type === 'ordered' ? 'ol' : 'ul'}
                data-unstyled-list={type === 'none'}
                stylexProps={stylex.props(styles.list)}
                ref={forwardedRef}
            />
        );
    },
);

(
    ListComponent as unknown as {
        /**
         * The display name of the list.
         */
        displayName: string;
    }
).displayName = 'List.Root';

export type { ListItemProps } from './ListItem';
export type { ListProps };
export { ListComponent as Root, ListItem as Item };
