import { useLocation, Routes, Route } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import Home from "../../pages/Home";
import Explore from "../../pages/Explore";
import Login from "../../pages/Login";
import Register from "../../pages/Register";
import PasswordReset from "../../pages/PasswordReset";
import Recommendations from "../../pages/Recommendations";
import Itineraries from "../../pages/Itineraries";
import Profile from "../../pages/Profile";
import HowToUse from "../../pages/HowToUse";

const pageVariants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

function Page({ children }) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.22, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Every route navigation fades/slides the new page in — this is what
 * turns "clicking a nav link" from an instant, jarring content swap into
 * something that actually feels like motion. AnimatePresence needs a
 * stable `key` that changes per-route (location.pathname) to know when
 * to run the exit animation on the outgoing page.
 */
export default function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<Page><Home /></Page>} />
        <Route path="/explore" element={<Page><Explore /></Page>} />
        <Route path="/login" element={<Page><Login /></Page>} />
        <Route path="/register" element={<Page><Register /></Page>} />
        <Route path="/password-reset" element={<Page><PasswordReset /></Page>} />
        <Route path="/recommendations" element={<Page><Recommendations /></Page>} />
        <Route path="/itineraries" element={<Page><Itineraries /></Page>} />
        <Route path="/profile" element={<Page><Profile /></Page>} />
        <Route path="/how-to-use" element={<Page><HowToUse /></Page>} />
      </Routes>
    </AnimatePresence>
  );
}
