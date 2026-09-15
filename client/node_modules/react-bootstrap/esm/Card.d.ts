import * as React from 'react';
import { BsPrefixProps, BsPrefixRefForwardingComponent } from './helpers';
import { Color, Variant } from './types';
export interface CardProps extends BsPrefixProps, React.HTMLAttributes<HTMLElement> {
    bg?: Variant;
    text?: Color;
    border?: Variant;
    body?: boolean;
}
declare const _default: BsPrefixRefForwardingComponent<"div", CardProps> & {
    Img: BsPrefixRefForwardingComponent<"img", import("./CardImg").CardImgProps>;
    Title: BsPrefixRefForwardingComponent<"div", import("./CardTitle").CardTitleProps>;
    Subtitle: BsPrefixRefForwardingComponent<"div", import("./CardSubtitle").CardSubtitleProps>;
    Body: BsPrefixRefForwardingComponent<"div", import("./CardBody").CardBodyProps>;
    Link: BsPrefixRefForwardingComponent<"a", import("./CardLink").CardLinkProps>;
    Text: BsPrefixRefForwardingComponent<"p", import("./CardText").CardTextProps>;
    Header: BsPrefixRefForwardingComponent<"div", import("./CardHeader").CardHeaderProps>;
    Footer: BsPrefixRefForwardingComponent<"div", import("./CardFooter").CardFooterProps>;
    ImgOverlay: BsPrefixRefForwardingComponent<"div", import("./CardImgOverlay").CardImgOverlayProps>;
};
export default _default;
