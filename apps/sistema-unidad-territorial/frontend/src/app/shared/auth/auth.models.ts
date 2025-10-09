export interface SigninRequestDto {
	email: string;
	password: string;
	remember?: boolean;
}

export interface RoleResponseDto {
	id: string;
	name: string;
	created_at: string;
}

export interface UserResponseDto {
	id: string;
	email: string | null;
	email_verified_at: string | null;
	status: string;
	roles: RoleResponseDto[];
	created_at: string;
	updated_at: string;
}

export interface TokenResponseDto {
	access_token: string;
	refresh_token: string;
	token_type: string;
	expires_in: number;
	user: UserResponseDto;
}

// ========================================
// INTERFACES PARA RECUPERACIÓN DE CONTRASEÑA
// ========================================
export interface PasswordResetRequestDto {
	email: string;
}

export interface PasswordResetResponseDto {
	message: string;
	reset_token_id: string;
	expires_in_minutes: number;
}

export interface PasswordResetCodeValidationRequestDto {
	email: string;
	code: string;
}

export interface PasswordResetCodeValidationResponseDto {
	message: string;
	reset_token_id: string;
	expires_at: string;
}

export interface PasswordResetConfirmRequestDto {
	reset_token: string;
	new_password: string;
	confirm_password: string;
}

export interface PasswordResetConfirmResponseDto {
	message: string;
}
