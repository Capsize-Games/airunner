import * as React from 'react';
import { OffcanvasProps } from './Offcanvas';
export type NavbarOffcanvasProps = Omit<OffcanvasProps, 'show'>;
declare const NavbarOffcanvas: React.ForwardRefExoticComponent<Omit<NavbarOffcanvasProps, "ref"> & React.RefAttributes<HTMLDivElement>>;
export default NavbarOffcanvas;
