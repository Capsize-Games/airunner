import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface CarouselItemProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    interval?: number;
}
declare const CarouselItem: BsPrefixRefForwardingComponent<'div', CarouselItemProps>;
export default CarouselItem;
