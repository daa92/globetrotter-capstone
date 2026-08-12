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
import Verify from "../../pages/Verify";
import AdminDashboard from "../../pages/AdminDashboard";

// Deliberately unlisted path — not referenced by any nav/link in the app,
// so it's only reachable by someone who already knows it. This is
// obscurity on top of, not instead of, the real access control: the page
// itself checks user.is_admin, and every API call it makes is re-checked
// server-side by get_current_admin regardless of how someone got here.
const ADMIN_PATH = "/admin-c746b9c7d7c57420";

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
        <Route path="/verify" element={<Page><Verify /></Page>} />
        <Route path={ADMIN_PATH} element={<Page><AdminDashboard /></Page>} />
      </Routes>
    </AnimatePresence>
  );
}
