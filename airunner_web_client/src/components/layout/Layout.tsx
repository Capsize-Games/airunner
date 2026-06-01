import { type ReactNode } from "react";
import Sidebar from "./Sidebar";
import AppNavbar from "./AppNavbar";
import RightSidebar from "./RightSidebar";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="app-layout">
      <AppNavbar />
      <div className="app-body">
        <Sidebar />
        <main className="main-content p-3">{children}</main>
        <RightSidebar />
      </div>
    </div>
  );
}
