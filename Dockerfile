# Use the official Ubuntu base image
FROM ubuntu:latest

# Update and install required packages, including SSH server
RUN apt-get update && \
    apt-get install -y openssh-server sudo && \
    mkdir /var/run/sshd && \
    echo 'root:12341234' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd && \
    echo "export VISIBLE=now" >> /etc/profile

# Allow root login by default (Optional)
RUN echo 'root:DockerPass' | chpasswd

# Expose SSH port
EXPOSE 22

# Start the SSH service
CMD ["/usr/sbin/sshd", "-D"]
