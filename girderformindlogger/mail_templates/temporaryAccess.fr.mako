## -*- coding: utf-8 -*-
<%include file="_header.mako"/>

<div style="max-width: 440px;">
    <p>
        Un jeton d'accès temporaire a été demandé en votre nom. Vous pouvez accéder au système
        ${brandName} à l'adresse
        <a href="${url}">${url}</a>
        Une fois que vous aurez accédé au système, vous aurez la possibilité de mettre à jour votre mot de passe.
    </p>

    <p>
        Si vous n'avez pas initié cette demande d'accès temporaire, vous pouvez ignorer
        ce message. L'accès temporaire n'est disponible qu'avec le lien fourni et expire 15 minutes après avoir été demandé.
    </p>
</div>

<%include file="_footer.mako"/>
