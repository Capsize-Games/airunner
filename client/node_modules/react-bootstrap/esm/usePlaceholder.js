"use client";

import classNames from 'classnames';
import { useBootstrapPrefix } from './ThemeProvider';
import { useCol } from './Col';
export default function usePlaceholder({
  animation,
  bg,
  bsPrefix,
  size,
  ...props
}) {
  bsPrefix = useBootstrapPrefix(bsPrefix, 'placeholder');
  const [{
    className,
    ...colProps
  }] = useCol(props);
  return {
    ...colProps,
    className: classNames(className, animation ? `${bsPrefix}-${animation}` : bsPrefix, size && `${bsPrefix}-${size}`, bg && `bg-${bg}`)
  };
}