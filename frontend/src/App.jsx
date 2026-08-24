import { BrowserRouter } from "react-router-dom";
import Layout from "./components/layout/Layout";
import AnimatedRoutes from "./components/layout/AnimatedRoutes";
import useActivityHeartbeat from "./hooks/useActivityHeartbeat";

export default function App() {
  useActivityHeartbeat();
  return (
    <BrowserRouter>
      <Layout>
        <AnimatedRoutes />
      </Layout>
    </BrowserRouter>
  );
}
