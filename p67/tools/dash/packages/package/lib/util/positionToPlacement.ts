import type { Placement } from 'react-aria';

import type { PopoverAlign, PopoverPosition } from '../Popover';

const placementMap: Record<
    `${PopoverPosition} ${PopoverAlign}` | PopoverPosition,
    Placement
> = {
    top: 'top',
    'top start': 'top start',
    'top center': 'top',
    'top end': 'top end',
    bottom: 'bottom',
    'bottom start': 'bottom start',
    'bottom center': 'bottom',
    'bottom end': 'bottom end',
    left: 'left',
    'left start': 'left top',
    'left center': 'left',
    'left end': 'left bottom',
    right: 'right',
    'right start': 'right top',
    'right center': 'right',
    'right end': 'right bottom',
};

export function positionToPlacement(
    position: PopoverPosition,
    align?: PopoverAlign,
) {
    const key = align ? (`${position} ${align}` as const) : position;
    return placementMap[key];
}
