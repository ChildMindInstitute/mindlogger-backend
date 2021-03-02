<%include file="_header.mako"/>

<div style="max-width: 440px;">
    <p>Someone has registered a new account that needs admin approval.</p>

    <p>Login: ${user.get('login')}</p>
    <p>Email: ${user.get('email')}</p>
    <p>Name: ${user.get('firstName')}</p>

    <p><a href="${url}">${url}</a></p>
</div>

<%include file="_footer.en.mako"/>
