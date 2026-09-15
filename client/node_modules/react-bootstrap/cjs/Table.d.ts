import * as React from 'react';
import { BsPrefixOnlyProps } from './helpers';
export interface TableProps extends BsPrefixOnlyProps, React.TableHTMLAttributes<HTMLTableElement> {
    striped?: boolean | string;
    bordered?: boolean;
    borderless?: boolean;
    hover?: boolean;
    size?: string;
    variant?: string;
    responsive?: boolean | string;
}
declare const Table: React.ForwardRefExoticComponent<TableProps & React.RefAttributes<HTMLTableElement>>;
export default Table;
