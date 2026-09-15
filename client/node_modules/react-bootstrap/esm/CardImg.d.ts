import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface CardImgProps extends BsPrefixProps, React.ImgHTMLAttributes<HTMLImageElement> {
    variant?: 'top' | 'bottom' | string;
}
declare const CardImg: BsPrefixRefForwardingComponent<'img', CardImgProps>;
export default CardImg;
