export interface LoginRequestDto {
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
