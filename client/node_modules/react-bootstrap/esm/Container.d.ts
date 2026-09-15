import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface ContainerProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    fluid?: boolean | string | 'sm' | 'md' | 'lg' | 'xl' | 'xxl';
}
declare const Container: BsPrefixRefForwardingComponent<'div', ContainerProps>;
export default Container;
