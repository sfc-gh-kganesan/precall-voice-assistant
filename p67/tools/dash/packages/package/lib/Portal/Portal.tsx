import { createPortal } from 'react-dom';

import { BaltoThemeProvider } from '../BaltoProvider';
import { useBaltoContext } from '../hooks';

export interface PortalProps extends React.ComponentPropsWithoutRef<'div'> {
    /**
     * The container to render the portal in.
     */
    container?: Element | DocumentFragment | null | undefined;
}

export const Portal = ({
    container,
    ...props
}: PortalProps): JSX.Element | null => {
    let { portalContainer } = useBaltoContext();

    if (!portalContainer && typeof window !== 'undefined') {
        portalContainer = document.body;
    }

    if (!portalContainer) {
        return null;
    }

    return createPortal(
        <BaltoThemeProvider>
            <div {...props} />
        </BaltoThemeProvider>,
        container || portalContainer,
    );
};
