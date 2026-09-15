import * as React from 'react';
import { AbstractModalHeaderProps } from './AbstractModalHeader';
import { BsPrefixOnlyProps } from './helpers';
export interface ModalHeaderProps extends AbstractModalHeaderProps, BsPrefixOnlyProps {
}
declare const ModalHeader: React.ForwardRefExoticComponent<ModalHeaderProps & React.RefAttributes<HTMLDivElement>>;
export default ModalHeader;
