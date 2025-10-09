import { UserResponseDto } from './auth.models';

/**
 * Utility functions for role-based operations
 */

export interface UserRole {
	id: string;
	name: string;
}

export interface RoleInfo {
	isAdmin: boolean;
	isModerator: boolean;
	isResident: boolean;
	hasAdminPrivileges: boolean;
	roles: UserRole[];
}

/**
 * Analyzes user roles and returns role information
 */
export function analyzeUserRoles(user: UserResponseDto | null): RoleInfo {
	if (!user || !user.roles) {
		return {
			isAdmin: false,
			isModerator: false,
			isResident: false,
			hasAdminPrivileges: false,
			roles: []
		};
	}

	const roleNames = user.roles.map(role => role.name.toUpperCase());
	
	const isAdmin = roleNames.includes('ADMIN') || roleNames.includes('SUPERADMIN');
	const isModerator = roleNames.includes('MODERATOR');
	const isResident = !isAdmin && !isModerator; // If not admin/moderator, consider as resident
	const hasAdminPrivileges = isAdmin || isModerator;

	return {
		isAdmin,
		isModerator,
		isResident,
		hasAdminPrivileges,
		roles: user.roles
	};
}

/**
 * Determines the appropriate dashboard route based on user roles
 */
export function getDashboardRoute(user: UserResponseDto | null): string {
	const roleInfo = analyzeUserRoles(user);

	if (roleInfo.hasAdminPrivileges) {
		return '/admin-dashboard';
	}

	// Default to resident dashboard for users without admin privileges
	return '/resident-dashboard';
}

/**
 * Checks if user has specific role
 */
export function hasRole(user: UserResponseDto | null, roleName: string): boolean {
	if (!user || !user.roles) {
		return false;
	}

	return user.roles.some(role => role.name.toUpperCase() === roleName.toUpperCase());
}

/**
 * Checks if user has any of the specified roles
 */
export function hasAnyRole(user: UserResponseDto | null, roleNames: string[]): boolean {
	if (!user || !user.roles) {
		return false;
	}

	const upperRoleNames = roleNames.map(name => name.toUpperCase());
	return user.roles.some(role => upperRoleNames.includes(role.name.toUpperCase()));
}
