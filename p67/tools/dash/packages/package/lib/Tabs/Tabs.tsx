import { useControlledState } from '@react-stately/utils';
import type { ReactHTML } from 'react';
import { forwardRef, useCallback, useRef } from 'react';
import { Tabs as TabsPrimitive } from 'react-aria-components';
import { Flex } from '../Layout';
import type { ControlledValueComponent } from '../util/Controlled';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { TabsContent } from './TabsContent';
import { TabsList } from './TabsList';
import { TabsTrigger } from './TabsTrigger';

interface TabsProps<T extends keyof ReactHTML = 'div'>
    extends ControlledValueComponent<string>,
        Omit<SlottedContainerProps<T>, 'defaultValue' | 'dir'> {}

const TabsComponent = forwardRef<HTMLDivElement, TabsProps>(
    (
        {
            defaultValue,
            value: valueProp,
            onValueChange: onValueChangeProp,
            ...props
        },
        forwardedRef,
    ) => {
        const [value, setValue] = useControlledState(
            valueProp,
            defaultValue ?? '',
            onValueChangeProp,
        );
        const transition = useRef<ReturnType<
            typeof document.startViewTransition
        > | null>(null);
        const onValueChange = useCallback(
            (newValue: string) => {
                if (transition.current) {
                    return;
                }

                setValue(newValue);
            },
            [setValue],
        );

        return (
            <Flex direction="column" gap="0x" asChild>
                <TabsPrimitive
                    {...props}
                    orientation="horizontal"
                    ref={forwardedRef}
                    selectedKey={value}
                    onSelectionChange={(e) => onValueChange(e as string)}
                />
            </Flex>
        );
    },
);

TabsComponent.displayName = 'Tabs.Root';

export type { TabsProps };
export type { TabsContentProps } from './TabsContent';
export type { TabsListProps } from './TabsList';
export type { TabsTriggerProps } from './TabsTrigger';
export {
    TabsComponent as Root,
    TabsList as List,
    TabsTrigger as Trigger,
    TabsContent as Content,
};
