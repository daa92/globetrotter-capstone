import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import Home from "./pages/Home";
import Explore from "./pages/Explore";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Recommendations from "./pages/Recommendations";
import Itineraries from "./pages/Itineraries";
import Profile from "./pages/Profile";
import HowToUse from "./pages/HowToUse";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/explore" element={<Explore />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/itineraries" element={<Itineraries />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/how-to-use" element={<HowToUse />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
