<?php
$publickey = "6LebytsUAAAAAKRKKc5_CzsAGHVrpjyWKZWAamrS";
$privatekey = "6LebytsUAAAAAKP-tUP6vsYvMiqyCMfv67XAvRqJ";
# the response from reCAPTCHA
$resp = null;
# the error code from reCAPTCHA, if any
$error = null;
session_start();
$_SESSION['test'] = 'bla~123';
setcookie('test', 'abc~def bla', time() + 3600);
setcookie('test2', 'bla', 0);
?>
<html>
<head>
    <title>reCAPTCHA demo: Simple page</title>
    <script src="https://www.google.com/recaptcha/api.js" async defer></script>
</head>
<body>
<form action="#" method="post">
    <?php
    # was there a reCAPTCHA response?
    if (isset($_POST["g-recaptcha-response"])) {
        $url = 'https://www.google.com/recaptcha/api/siteverify';
        $data = array(
            'secret' => $privatekey,
            'response' => $_POST["g-recaptcha-response"]
        );
        $options = array(
            'http' => array (
                'method' => 'POST',
                'content' => http_build_query($data)
            )
        );
        $context  = stream_context_create($options);
        $verify = file_get_contents($url, false, $context);
        $captcha_success=json_decode($verify, TRUE);
        echo '<div>',print_r($verify, TRUE),'</div>';
    }
    ?>
    <div class="g-recaptcha" data-sitekey="<?php echo $publickey; ?>"></div>
    <br/>
    <input type="submit" value="Submit">
</form>
<div>
	<?php
    if ( ! isset($_SESSION['ua']))
    {
        $_SESSION['ua'] = $_SERVER['HTTP_USER_AGENT'];
    }
    if ($_SESSION['ua'] != $_SERVER['HTTP_USER_AGENT'])
    {
		echo 'User-Agent Mismatch';
    }
    ?>
</div>
<div>Server:
<?php echo print_r($_SERVER, TRUE); ?>
</div>
<div>Session:
    <?php
	if (isset($_SESSION))
	{
    	echo print_r($_SESSION, TRUE);
	}
	?>
</div>
<div>Cookie:
    <?php echo print_r($_COOKIE, TRUE); ?>
</div>
<div>Post:
    <?php echo print_r($_POST, TRUE); ?>
</div>
</body>
</html>
