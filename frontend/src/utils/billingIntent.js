// Shared between BillingPage.jsx's Team-License-first nudge and
// SceneViewer.jsx's analyze-redirect toast — both must use the exact
// same condition so they can't drift out of sync with each other.
export const isNeverSubscribedTeamIntent = (entitlement) => {
    if (!entitlement) return false;
    return entitlement.signup_plan === 'tier_2_annual_team'
        && entitlement.tier === 'none'
        && entitlement.status === 'none';
};
