import request from '@/utils/request'

export function login(data) {
  return request.post('/api/auth/login', data)
}

export function register(data) {
  return request.post('/api/auth/register', data)
}

export function getCurrentUser() {
  return request.get('/api/auth/me')
}

export function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('user_name')
  localStorage.removeItem('nickname')
  localStorage.removeItem('user_role')
  localStorage.removeItem('role')
  localStorage.removeItem('userInfo')
  localStorage.removeItem('user_info')
  localStorage.removeItem('user')

  return Promise.resolve({
    code: 200,
    message: '退出成功',
  })
}

// 兼容旧代码里可能使用的命名
export const loginApi = login
export const registerApi = register
export const logoutApi = logout
export const getUserInfo = getCurrentUser