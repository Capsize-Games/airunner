import * as React from 'react';
import { TabsProps as BaseTabsProps } from '@restart/ui/Tabs';
import { NavProps } from './Nav';
import { TransitionType } from './helpers';
export interface TabsProps extends Omit<BaseTabsProps, 'transition'>, Omit<React.HTMLAttributes<HTMLElement>, 'onSelect'>, NavProps {
    transition?: TransitionType;
}
declare const Tabs: React.FC<TabsProps>;
export default Tabs;
