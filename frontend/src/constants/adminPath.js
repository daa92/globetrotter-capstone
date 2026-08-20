// src/constants/adminPath.js
//
// The admin dashboard is reachable two ways, per design: this fixed
// unguessable path (bookmarkable, works even if you're not sure you're
// logged in yet), and — for signed-in admins — a normal nav link in
// Navbar.jsx. Neither is the real access control: the page itself checks
// user.is_admin/is_principal_admin, and every API call it makes is
// re-checked server-side (get_current_admin / require_permission /
// get_current_principal_admin). Showing a nav link to admins doesn't
// weaken that — a non-admin still can't do anything at this URL even if
// they find it some other way.
export const ADMIN_PATH = "/admin-c746b9c7d7c57420";
