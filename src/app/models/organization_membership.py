"""Public membership name; retain the existing table and import for compatibility."""

from app.models.associations.organization_user import OrganizationUser

OrganizationMembership = OrganizationUser
