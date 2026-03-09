import type { IconProps } from '@snowflake/stellar-icons';
import { CheckCircleIcon } from '@snowflake/stellar-icons/CheckCircleIcon';
import { InfoCircleIcon } from '@snowflake/stellar-icons/InfoCircleIcon';
import { WarningTriangleIcon } from '@snowflake/stellar-icons/WarningTriangleIcon';
import { useContext } from 'react';
import { devError } from '../../util/dev-warning';
import { StatusContext } from './StatusContext';

export const StatusIcon = (props: IconProps) => {
    const ctx = useContext(StatusContext);

    if (ctx === null) {
        devError('Status Icon can only be used within a Status Context');
    }

    const Component =
        ctx?.variant === 'critical' || ctx?.variant === 'caution'
            ? WarningTriangleIcon
            : ctx?.variant === 'success'
              ? CheckCircleIcon
              : InfoCircleIcon;
    return <Component {...props} />;
};
