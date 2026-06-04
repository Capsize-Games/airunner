import { NavLink, useLocation } from "react-router-dom";
import Navbar from "react-bootstrap/Navbar";
import Nav from "react-bootstrap/Nav";
import Container from "react-bootstrap/Container";

export default function AppNavbar() {
  const location = useLocation();

  return (
    <Navbar bg="dark" variant="dark" className="app-navbar">
      <Container fluid>
        <Navbar.Brand as={NavLink} to="/">
          🎨 AI Runner
        </Navbar.Brand>
        <Nav className="me-auto" activeKey={location.pathname}>
          <Nav.Link as={NavLink} to="/chat" eventKey="/chat">
            💬 Chat
          </Nav.Link>
          <Nav.Link as={NavLink} to="/art" eventKey="/art">
            🖼️ Art
          </Nav.Link>
          <Nav.Link as={NavLink} to="/documents" eventKey="/documents">
            📄 Documents
          </Nav.Link>
          <Nav.Link as={NavLink} to="/downloads" eventKey="/downloads">
            ⬇️ Downloads
          </Nav.Link>
          <Nav.Link as={NavLink} to="/settings" eventKey="/settings">
            ⚙️ Settings
          </Nav.Link>
        </Nav>
      </Container>
    </Navbar>
  );
}
