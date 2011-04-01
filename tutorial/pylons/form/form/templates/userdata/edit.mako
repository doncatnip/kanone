<form action="${h.url(controller='userdata',action='edit')}" method="POST">
    Name: <input type="text" name="name" value="${form('name').value}"/><br />
    ${form('name').error|n}
    Email: <input type="text" name="email" value="${form('email').value}"/><br />
    ${form('email').error|n}
    <input type="submit" value="Submit" />
</form>
