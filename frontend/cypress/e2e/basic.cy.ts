describe('Basic E2E Tests', () => {
  it('should load the homepage', () => {
    cy.visit('/')
    cy.contains('CapSight')
  })

  it('should protect admin routes', () => {
    cy.request({
      url: '/admin',
      failOnStatusCode: false
    }).then((response) => {
      expect(response.status).to.eq(401)
    })
  })
})
