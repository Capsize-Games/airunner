import * as React from 'react';
import { AbstractModalHeaderProps } from './AbstractModalHeader';
import { BsPrefixOnlyProps } from './helpers';
export interface OffcanvasHeaderProps extends AbstractModalHeaderProps, BsPrefixOnlyProps {
}
declare const OffcanvasHeader: React.ForwardRefExoticComponent<OffcanvasHeaderProps & React.RefAttributes<HTMLDivElement>>;
export default OffcanvasHeader;
