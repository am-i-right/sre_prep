terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  type    = string
  default = "dev"
}

resource "terraform_data" "sre_lab" {
  input = {
    environment = var.environment
    service     = "flask-app"
    slo         = "99.9%"
  }
}

output "configuration" {
  value = terraform_data.sre_lab.output
}
