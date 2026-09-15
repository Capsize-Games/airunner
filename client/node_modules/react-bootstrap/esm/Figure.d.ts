import * as React from 'react';
import type { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
export interface FigureProps extends BsPrefixProps, React.AnchorHTMLAttributes<HTMLElement> {
}
declare const _default: BsPrefixRefForwardingComponent<"figure", FigureProps> & {
    Image: React.ForwardRefExoticComponent<import("./Image").ImageProps & React.RefAttributes<HTMLImageElement>>;
    Caption: BsPrefixRefForwardingComponent<"figcaption", import("./FigureCaption").FigureCaptionProps>;
};
export default _default;
