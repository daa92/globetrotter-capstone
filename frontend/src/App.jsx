import { BrowserRouter } from "react-router-dom";
import Layout from "./components/layout/Layout";
import AnimatedRoutes from "./components/layout/AnimatedRoutes";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <AnimatedRoutes />
      </Layout>
    </BrowserRouter>
  );
}
