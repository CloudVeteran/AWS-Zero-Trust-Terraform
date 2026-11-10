output "vpc_id" {
  value = aws_vpc.main.id
}

output "verified_access_instance_id" {
  value = aws_verifiedaccess_instance.main.id
}
