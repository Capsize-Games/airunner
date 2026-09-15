import { ColProps } from './Col';
import { Variant } from './types';
export type PlaceholderAnimation = 'glow' | 'wave';
export type PlaceholderSize = 'xs' | 'sm' | 'lg';
export interface UsePlaceholderProps extends Omit<ColProps, 'as'> {
    animation?: PlaceholderAnimation;
    bg?: Variant;
    size?: PlaceholderSize;
}
export default function usePlaceholder({ animation, bg, bsPrefix, size, ...props }: UsePlaceholderProps): any;
